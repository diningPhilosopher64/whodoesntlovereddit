import boto3, click, pprint, json
import check_table
from json import JSONDecodeError


pp = pprint.PrettyPrinter(indent=2, compact=True, width=80)
ddb = boto3.client("dynamodb")


@click.command()
@click.option("--table_name", type=str, help="Name of the table")
@click.option(
    "--file_path",
    type=str,
    help="Path to the python file containing the item to get",
)
def main(table_name, file_path):
    if check_table.not_exists(table_name):
        raise Exception("\n\nTable doesn't exist. Check the table name\n")
    try:
        with open(file_path, "r") as f:
            item = json.loads(f.read())

        response = ddb.get_item(TableName=table_name, Key=item)
        pp.pprint(response["Item"])

    except JSONDecodeError as decode_error:
        print(f"Unable to parse JSON data from the file at {file_path}")

    except Exception as e:
        print(f"Failed with Exception: {e.args[0]}")


if __name__ == "__main__":
    main()
