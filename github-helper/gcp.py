"""GCP VM creation via gcloud CLI."""

import datetime

import shlex
import subprocess


ZONES = [
      "us-central1-a",
      "us-central1-b",
      "us-central1-c",
      "us-central1-f",
      "us-east1-b",
      "us-east1-c",
      "us-east1-d",
      "us-west1-a",
      "us-west1-b",
      "us-west1-c",
]

MACHINE_TYPES = [
      "e2-micro",
      "e2-small",
      "e2-medium",
      "e2-standard-4",
      "e2-standard-8",
      "n2-standard-2",
      "n2-standard-4",
      "n2-standard-8",
]


def prompt_with_default(question: str, default: str) -> str:
    prompt = f"{question} [{default}]: " if default else f"{question}: "
    response = input(prompt).strip()
    return response if response else default


def build_gcloud_vm_create_command(
    project: str = None,
    zone: str = None,
    instance_name: str = None,
    machine_type: str = None,
    image_family: str = None,
    disk_size: str = None,
) -> str:
    """Build a gcloud compute instances create command."""
    from settings import get_settings

    defaults = get_settings()

    parts = ["gcloud compute instances create"]

    if project is None:
        project = defaults.get("default-gcp-project", "") or ""
    if not project:
        project = prompt_with_default("GCP Project", "")

    if instance_name is None:
        instance_name = prompt_with_default(
            "Instance name",
            f"vm-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
        )

    if zone is None:
        zone = defaults.get("default-gcp-vm-zone", "") or ""
    if not zone:
        print("\nAvailable zones:")
        for i, z in enumerate(ZONES):
            print(f"    {i+1}. {z}")
        zone_idx = prompt_with_default("Zone index", "1")
        if zone_idx.isnumeric():
            idx = int(zone_idx) - 1
            if 0 <= idx < len(ZONES):
                zone = ZONES[idx]
        if not zone:
            zone = ZONES[0]

    if machine_type is None:
        machine_type = defaults.get("default-gcp-vm-machine", "") or ""
    if not machine_type:
        print("\nAvailable machine types:")
        for i, mt in enumerate(MACHINE_TYPES):
            print(f"    {i+1}. {mt}")
        mt_idx = prompt_with_default("Machine type index", "3")
        if mt_idx.isnumeric():
            idx = int(mt_idx) - 1
            if 0 <= idx < len(MACHINE_TYPES):
                machine_type = MACHINE_TYPES[idx]
        if not machine_type:
            machine_type = MACHINE_TYPES[2]

#      # Defaults for image and disk, not working
#    if image_family is None:
#        image_family = defaults.get("default-gcp-vm-image", "") or "ubuntu-2204-lts"
#    elif not image_family:
#        image_family = "ubuntu-2204-lts"

    if disk_size is None:
        disk_size = defaults.get("default-gcp-vm-disk-size", "") or "20"
    elif not disk_size:
        disk_size = prompt_with_default("Disk size (GB)", "20")

      # Build command with project/instance/zone/machine/image/disk
    parts.append(f"--project={shlex.quote(project)}")
    parts.append(shlex.quote(instance_name))
    parts.append(f"--zone={shlex.quote(zone)}")
    parts.append(f"--machine-type={shlex.quote(machine_type)}")
#    parts.append(f"--image-family={shlex.quote(image_family)}")
    parts.append(f"--boot-disk-size={disk_size}")
    parts.append("--boot-disk-type=pd-standard")

      # Resource manager tags, not working
#    raw_tags = defaults.get("default-gcp-resource-manager-tags", "")
#    if raw_tags and ":" in raw_tags:
#        key, value = raw_tags.split(":", 1)
#        parts.append(f'--resource-manager-tags=tagKeys/{key}=tagValues/{value}')

    return " ".join(parts)


def handle_gcp(args) -> int:
    cmd = build_gcloud_vm_create_command(
        project=getattr(args, "project", None),
        zone=getattr(args, "zone", None),
        instance_name=getattr(args, "name", None),
        machine_type=getattr(args, "machine", None),
        image_family=getattr(args, "image", None),
        disk_size=getattr(args, "disk", None),
    )

    if getattr(args, "dry_run", False):
        print(f"Dry-run mode. Command:\n{cmd}")
        return 0

    confirmation = prompt_with_default(cmd + "\nRun this command?", "y").lower()
    if confirmation == "y":
        completed = subprocess.run(shlex.split(cmd), check=False)
        return completed.returncode

    print("Cancelled.")
    return 1


def handle_dss_conf(args) -> int:
    print("To get the desired URL for DSS installation, visit:")
    print("https://downloads.dataiku.com/public/dss/")
    subprocess.run(["mkdir", "dss"], check=False)
    subprocess.run(["cd", "dss"], check=False)
    return 0
