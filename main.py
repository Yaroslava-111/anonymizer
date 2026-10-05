import argparse
import os
import sys
from datetime import datetime, timezone

import pandas as pd
from rich.console import Console
from rich.table import Table

from anonymizer import anonymize_dataframe
from column_detector import detect_personal_columns, suggest_columns_for_anonymization
from crypto_utils import decrypt_mapping, encrypt_mapping
from deanonymizer import deanonymize_dataframe
from mapping_store import create_empty_mapping, load_mapping, save_mapping

console = Console()


def detect_file_type(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".csv":
        return "csv"
    elif ext in (".xlsx", ".xls"):
        return "excel"
    else:
        return "csv"


def load_dataframe(filepath):
    ft = detect_file_type(filepath)
    if ft == "csv":
        return pd.read_csv(filepath, encoding="utf-8")
    else:
        return pd.read_excel(filepath, engine="openpyxl")


def save_dataframe(df, filepath):
    ft = detect_file_type(filepath)
    if ft == "csv":
        df.to_csv(filepath, index=False, encoding="utf-8")
    else:
        df.to_excel(filepath, index=False, engine="openpyxl")


def interactive_column_selection(detected):
    console.print("\n[bold]Выберите колонки для анонимизации[/bold] (через запятую или 'all'):")
    choice = input("> ").strip()
    if choice.lower() == "all":
        return [col for col, _ in detected]
    indices = [int(x.strip()) - 1 for x in choice.split(",")]
    return [detected[i][0] for i in indices if 0 <= i < len(detected)]


def cmd_anonymize(args):
    if not os.path.exists(args.input):
        console.print(f"[red]Файл не найден: {args.input}[/red]")
        sys.exit(1)

    df = load_dataframe(args.input)
    console.print(f"[green]Загружено {len(df)} строк, {len(df.columns)} колонок.[/green]")

    existing_mapping = None
    if args.mapping and os.path.exists(args.mapping):
        existing_mapping = load_mapping(args.mapping)
        console.print(f"[blue]Загружен существующий маппинг: {args.mapping}[/blue]")

    if args.columns:
        columns = [c.strip() for c in args.columns.split(",")]
    else:
        detected = suggest_columns_for_anonymization(df)
        if not detected:
            console.print("[yellow]Укажите колонки вручную через --columns[/yellow]")
            sys.exit(1)
        columns = interactive_column_selection(detected)

    console.print("\n[bold cyan]Анонимизация...[/bold cyan]")
    anon_df, mapping, stats = anonymize_dataframe(df, columns, existing_mapping)
    for col, count in stats.items():
        console.print(f"  {col}: {count} уникальных значений → индексы 1-{count}")

    output = args.output
    if not output:
        base, ext = os.path.splitext(args.input)
        output = f"{base}_anonymous{ext}"

    mapping_file = args.mapping
    if not mapping_file:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        mapping_file = f"mapping_{ts}.json"

    save_dataframe(anon_df, output)
    save_mapping(mapping, mapping_file)

    console.print(f"\n[green]Сохранено:[/green]")
    console.print(f"  Таблица: {output}")
    console.print(f"  Маппинг: {mapping_file}")
    console.print(f"\n[bold green]Готово.[/bold green] Для восстановления:")
    console.print(f"  python main.py deanonymize --input {output} --mapping {mapping_file}")


def cmd_deanonymize(args):
    if not os.path.exists(args.input):
        console.print(f"[red]Файл не найден: {args.input}[/red]")
        sys.exit(1)
    if not os.path.exists(args.mapping):
        console.print(f"[red]Маппинг не найден: {args.mapping}[/red]")
        sys.exit(1)

    df = load_dataframe(args.input)
    mapping = load_mapping(args.mapping)
    console.print(f"[green]Загружено {len(df)} строк.[/green]")

    restored_df, stats = deanonymize_dataframe(df, mapping)

    output = args.output
    if not output:
        base, ext = os.path.splitext(args.input)
        output = f"{base}_restored{ext}"

    save_dataframe(restored_df, output)

    table = Table(title="Статистика восстановления")
    table.add_column("Колонка", style="cyan")
    table.add_column("Всего", style="green")
    table.add_column("Не найдено", style="red")
    for col_name, s in stats.items():
        table.add_row(col_name, str(s["total"]), str(s["unmapped"]))
    console.print(table)
    console.print(f"\n[green]Восстановленная таблица: {output}[/green]")


def cmd_info(args):
    if not os.path.exists(args.mapping):
        console.print(f"[red]Маппинг не найден: {args.mapping}[/red]")
        sys.exit(1)

    mapping = load_mapping(args.mapping)
    console.print(f"[bold]Версия:[/bold] {mapping.get('version')}")
    console.print(f"[bold]Создан:[/bold] {mapping.get('created_at')}")

    table = Table(title="Колонки в маппинге")
    table.add_column("Колонка", style="cyan")
    table.add_column("Тип", style="green")
    table.add_column("Уникальных значений", style="yellow")
    for col_name, col_data in mapping.get("columns", {}).items():
        table.add_row(col_name, col_data.get("type", "?"), str(len(col_data.get("mapping", {}))))
    console.print(table)


def cmd_encrypt(args):
    if not os.path.exists(args.mapping):
        console.print(f"[red]Маппинг не найден: {args.mapping}[/red]")
        sys.exit(1)

    mapping = load_mapping(args.mapping)
    encrypted = encrypt_mapping(mapping, args.password)

    output = args.output
    if not output:
        output = os.path.splitext(args.mapping)[0] + ".enc"

    with open(output, "w", encoding="utf-8") as f:
        f.write(encrypted)

    console.print(f"[green]Зашифрованный маппинг сохранён: {output}[/green]")


def cmd_decrypt(args):
    if not os.path.exists(args.mapping):
        console.print(f"[red]Файл не найден: {args.mapping}[/red]")
        sys.exit(1)

    with open(args.mapping, "r", encoding="utf-8") as f:
        encrypted = f.read()

    try:
        mapping = decrypt_mapping(encrypted, args.password)
    except Exception:
        console.print("[red]Ошибка расшифрования. Неверный пароль или повреждённый файл.[/red]")
        sys.exit(1)

    output = args.output
    if not output:
        output = os.path.splitext(args.mapping)[0] + "_decrypted.json"

    save_mapping(mapping, output)
    console.print(f"[green]Маппинг расшифрован и сохранён: {output}[/green]")


def main():
    parser = argparse.ArgumentParser(
        description="Локальное приложение анонимизации табличных данных",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Команда")

    p_anon = subparsers.add_parser("anonymize", help="Анонимизация таблицы")
    p_anon.add_argument("--input", "-i", required=True, help="Входной файл (xlsx/csv)")
    p_anon.add_argument("--output", "-o", help="Выходной файл (по умолчанию *_anonymous*)")
    p_anon.add_argument("--mapping", "-m", help="Файл маппинга (JSON)")
    p_anon.add_argument("--columns", "-c", help="Колонки через запятую")

    p_deanon = subparsers.add_parser("deanonymize", help="Деанонимизация таблицы")
    p_deanon.add_argument("--input", "-i", required=True, help="Анонимизированный файл")
    p_deanon.add_argument("--mapping", "-m", required=True, help="Файл маппинга (JSON)")
    p_deanon.add_argument("--output", "-o", help="Выходной файл")

    p_info = subparsers.add_parser("info", help="Информация о маппинге")
    p_info.add_argument("--mapping", "-m", required=True, help="Файл маппинга (JSON)")

    p_encrypt = subparsers.add_parser("encrypt-mapping", help="Шифрование маппинга")
    p_encrypt.add_argument("--mapping", "-m", required=True, help="Файл маппинга (JSON)")
    p_encrypt.add_argument("--password", "-p", required=True, help="Пароль")
    p_encrypt.add_argument("--output", "-o", help="Выходной файл (.enc)")

    p_decrypt = subparsers.add_parser("decrypt-mapping", help="Расшифрование маппинга")
    p_decrypt.add_argument("--mapping", "-m", required=True, help="Зашифрованный файл (.enc)")
    p_decrypt.add_argument("--password", "-p", required=True, help="Пароль")
    p_decrypt.add_argument("--output", "-o", help="Выходной файл (JSON)")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "anonymize": cmd_anonymize,
        "deanonymize": cmd_deanonymize,
        "info": cmd_info,
        "encrypt-mapping": cmd_encrypt,
        "decrypt-mapping": cmd_decrypt,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
