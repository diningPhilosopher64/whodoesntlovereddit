import os, shutil, click
from pathlib import Path


@click.command()
@click.option("--src", type=str, help="Source folder")
@click.option("--dest", type=str, help="Destination folder")
@click.option(
    "--delete",
    type=bool,
    help="Deleting existing destination",
    default=False,
    show_default=True,
)
def main(src, dest, delete):
    src = Path(src)
    dest = Path(dest)

    if not delete:
        print(
            "\n--delete flag should be set to True.\nThis will delete destination folder before copying the src tree",
        )

    if str(src) not in str(dest):
        print(
            "You should have the same directory name at the end of dest or else the contents of lambda would be deleted."
        )

    try:
        shutil.rmtree(dest)
    except:
        pass

    shutil.copytree(src, dest)


if __name__ == "__main__":
    main()
