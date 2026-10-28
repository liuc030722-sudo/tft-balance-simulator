"""Command-line interface for read-only PostgreSQL queries."""

import argparse
import json

from tft_simulator.database.queries import (
    get_ability, get_champion, get_counts, list_champions, list_versions,
    read_connection,
)


def main() -> int:
    # 子命令把查询用途分开，业务查询本身仍放在queries.py中以便复用。
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("versions", help="List imported version snapshots")
    for command in ("list", "show", "counts"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--version-id", type=int, required=True)
        if command == "list":
            subparser.add_argument("--cost", type=int, choices=range(1, 6))
        elif command == "show":
            subparser.add_argument("--champion-id", required=True)
    args = parser.parse_args()
    if args.command != "versions" and args.version_id <= 0:
        parser.error("--version-id must be positive")

    with read_connection() as connection:
        if args.command == "versions":
            result = list_versions(connection)
        elif args.command == "list":
            result = list_champions(connection, args.version_id, args.cost)
        elif args.command == "counts":
            result = get_counts(connection, args.version_id)
        else:
            champion = get_champion(connection, args.version_id, args.champion_id)
            if champion is None:
                print("No champion found for that version and ID.")
                return 1
            result = {
                "champion": champion,
                "ability": get_ability(connection, args.version_id, args.champion_id),
            }
    # default=str仅为JSON输出转换日期/时间，不输出连接配置或凭据。
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    # 退出码区分成功和找不到英雄，便于终端及后续自动化调用。
    raise SystemExit(main())
