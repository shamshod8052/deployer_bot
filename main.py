"""
Telegram bot to receive student project ZIPs and deploy them to the server using Docker.

Features:
- Accepts ZIP files from authorized admins only
- Unpacks ZIP into /srv/bots/{project_name}_{timestamp}
- If ZIP contains a Dockerfile, uses it. Otherwise generates a safe default Dockerfile for Python bots
- Builds a Docker image and runs a container with resource limits
- /list to list running bot containers created by this tool
- /logs <container_name> to fetch last logs
- /stop <container_name> and /remove <container_name> to manage containers

Security notes (read carefully):
- This tool runs untrusted student code! Always run on a host with Docker, with appropriate user namespaces, and not on a production host with sensitive data.
- Prefer running in a VM or dedicated host.
- Consider enabling user namespaces, swap limits, cgroups, and additional sandboxing (gVisor, Firecracker) for stronger isolation.

Server prerequisites:
- Docker installed and the user running this script must be able to run `docker` (sudo or Docker group)
- Python 3.10+
- pip install -r requirements.txt: aiogram>=3.0

Usage:
- Fill BOT_TOKEN and ADMINS in the file or set as env vars
- Run: python main.py
- Send a ZIP file to the bot with caption: name:mybot (optional). If no name provided, the filename is used

"""

import asyncio
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, FSInputFile, ContentType
from dotenv import load_dotenv

load_dotenv()

# ---- CONFIGURATION ---------------------------------------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN") or "REPLACE_WITH_YOUR_BOT_TOKEN"
ADMINS = {int(x) for x in os.getenv("ADMINS", "").split(',') if x.strip()} or {123456789}
BASE_DIR = Path(os.getenv("DEPLOY_BASE", "~/projects/bots"))
DOCKER_RUN_EXTRA = os.getenv("DOCKER_RUN_EXTRA", "")
DEFAULT_PYTHON_IMAGE = os.getenv("DEFAULT_PYTHON_IMAGE", "python:3.11-slim")
DOCKER_BUILD_TIMEOUT = 300
# -----------------------------------------------------------------------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def sanitize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9_.-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or f"bot-{int(time.time())}"


def ensure_base_dir():
    BASE_DIR.mkdir(parents=True, exist_ok=True)



async def run_cmd(cmd, cwd=None, timeout=None):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=cwd,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return False, b"TIMEOUT"
    return proc.returncode == 0, out.decode(errors="ignore")


def generate_default_dockerfile(project_dir: Path):
    has_req = (project_dir / "requirements.txt").exists()
    has_pyproject = (project_dir / "pyproject.toml").exists()

    dockerfile = project_dir / "Dockerfile"
    if dockerfile.exists():
        return False

    lines = [f"FROM {DEFAULT_PYTHON_IMAGE}", "WORKDIR /app"]
    if has_req:
        lines += ["COPY requirements.txt ./", "RUN pip install --no-cache-dir -r requirements.txt"]
    elif has_pyproject:
        lines += ["COPY pyproject.toml ./", "RUN pip install --no-cache-dir ."]
    else:
        lines += ["# No requirements detected", "# If your bot needs packages, add requirements.txt to ZIP"]

    lines += ["COPY . .", "CMD [\"python\", \"main.py\"]"]
    dockerfile.write_text("\n".join(lines))
    return True


async def build_and_run(project_dir: Path, image_tag: str, container_name: str):
    success, out = await run_cmd(f"docker build -t {image_tag} .", cwd=str(project_dir), timeout=DOCKER_BUILD_TIMEOUT)
    if not success:
        return False, f"Build failed:\n{out}"

    await run_cmd(f"docker rm -f {container_name} || true")

    run_cmd_line = (
        f"docker run -d --name {container_name} --restart=always --memory=256m --cpus=0.5 {DOCKER_RUN_EXTRA} {image_tag}"
    )
    success, out = await run_cmd(run_cmd_line)
    if not success:
        return False, f"Run failed:\n{out}"

    return True, out


# ---- BOT HANDLERS ----------------------------------------------------------

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Hi! I'm DeployBot. Send me a ZIP of the student's project (as a file) and I will build & run it in Docker.\nOnly admins can use this bot.\nCommands: /list /logs <name> /stop <name> /remove <name>"
    )


def is_admin(user_id: int) -> bool:
    return user_id in ADMINS


@dp.message(F.document)
async def handle_zip(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("You are not allowed to deploy.")
        return

    doc = message.document
    if not doc.file_name.lower().endswith(".zip"):
        await message.answer("Please upload a .zip file containing the project.")
        return

    caption = (message.caption or "").strip()
    name = None
    m = re.search(r"name:([a-zA-Z0-9_.-]+)", caption)
    if m:
        name = m.group(1)
    else:
        name = Path(doc.file_name).stem

    name = sanitize_name(name)
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    project_dir = BASE_DIR / f"{name}_{ts}"
    ensure_base_dir()
    project_dir.mkdir(parents=True, exist_ok=True)

    await message.answer(f"Receiving {doc.file_name}... saving to {project_dir}")
    file_path = project_dir / doc.file_name
    await bot.download(doc, destination=file_path)

    try:
        shutil.unpack_archive(str(file_path), str(project_dir))
    except Exception as e:
        await message.answer(f"Failed to extract zip: {e}")
        return

    generated = generate_default_dockerfile(project_dir)
    if generated:
        await message.answer("No Dockerfile found, generated a default Dockerfile (expects main.py or requirements.txt).")

    image_tag = f"deploybot/{name}:{ts}"
    container_name = f"deploy_{name}_{ts}"

    msg = await message.answer("Building Docker image, this may take a minute...")
    success, out = await build_and_run(project_dir, image_tag, container_name)
    if success:
        await msg.edit_text(f"✅ Deployed as container `{container_name}` using image `{image_tag}`.\nUse /list to see running ones.", parse_mode="Markdown")
    else:
        await msg.edit_text(f"❌ Deployment failed:\n{out}")


@dp.message(Command("list"))
async def cmd_list(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("You are not allowed to use this command.")
        return
    ok, out = await run_cmd("docker ps --format \"{{.Names}}\t{{.Image}}\t{{.Status}}\"")
    if not ok:
        await message.answer("Failed to list containers. Is Docker running on this host?")
        return
    text = out.strip() or "No running containers"
    await message.answer(f"Running containers:\n<pre>{text}</pre>", parse_mode="HTML")


@dp.message(Command("logs"))
async def cmd_logs(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        await message.answer("You are not allowed to use this command.")
        return
    if not command.args:
        await message.answer("Usage: /logs <container_name>")
        return
    name = command.args.strip()
    ok, out = await run_cmd(f"docker logs --tail 200 {name}")
    if not ok:
        await message.answer(f"Failed to fetch logs for {name}.\n{out}")
        return
    if len(out) > 3900:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            f.write(out.encode())
            tmp_name = f.name
        await message.answer_document(FSInputFile(tmp_name), caption=f"Logs for {name}")
        try:
            os.unlink(tmp_name)
        except:
            pass
    else:
        await message.answer(f"Logs for {name}:\n<pre>{out}</pre>", parse_mode="HTML")


@dp.message(Command("stop"))
async def cmd_stop(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        await message.answer("You are not allowed to use this command.")
        return
    if not command.args:
        await message.answer("Usage: /stop <container_name>")
        return
    name = command.args.strip()
    ok, out = await run_cmd(f"docker stop {name}")
    if not ok:
        await message.answer(f"Failed to stop {name}:\n{out}")
    else:
        await message.answer(f"Stopped {name}")


@dp.message(Command("remove"))
async def cmd_remove(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        await message.answer("You are not allowed to use this command.")
        return
    if not command.args:
        await message.answer("Usage: /remove <container_name>")
        return
    name = command.args.strip()
    ok, out = await run_cmd(f"docker rm -f {name}")
    if not ok:
        await message.answer(f"Failed to remove {name}:\n{out}")
    else:
        await message.answer(f"Removed {name}")


# ---- STARTUP ---------------------------------------------------------------

async def main():
    print("Starting DeployBot...")
    ensure_base_dir()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
