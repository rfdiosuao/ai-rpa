"""Office automation scenario templates and helpers."""

from __future__ import annotations

# Common office automation script templates (used as AI prompt examples)
OFFICE_EXAMPLES = """
示例 - 读取Excel文件:
*** Settings ***
Library    RPA.Excel.Files

*** Test Cases ***
Read Excel Data
    Open Workbook    data.xlsx
    ${value}=    Read Cell    A1
    Log    Cell A1 value: ${value}
    Close Workbook

示例 - 创建Excel文件并写入数据:
*** Settings ***
Library    RPA.Excel.Files

*** Test Cases ***
Create Excel File
    Create Workbook    output.xlsx
    Write Cell    1    A    Hello
    Write Cell    1    B    World
    Save Workbook
    Close Workbook

示例 - 发送邮件:
*** Settings ***
Library    RPA.Email.ImapSmtp

*** Test Cases ***
Send Email
    Authorize    account@gmail.com    password    smtp.gmail.com    imap.gmail.com
    Send Message    sender@gmail.com    recipient@example.com    Test Subject    Email body text
"""
