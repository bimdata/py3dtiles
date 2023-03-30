from pathlib import Path

from py3dtiles.tileset.content import read_binary_tile_content


def main(args):
    try:
        tile_content = read_binary_tile_content(args.file)
    except ValueError as e:
        print(f"Error when reading the file {args.file}")
        raise e

    tile_content.print_info()


def init_parser(subparser):
    # arg parse
    parser = subparser.add_parser(
        "info", help="Extract information from a 3DTiles file"
    )

    parser.add_argument("file", type=Path)

    return parser
