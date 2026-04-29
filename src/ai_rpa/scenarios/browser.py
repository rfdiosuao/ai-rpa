"""Browser automation scenario templates and helpers."""

from __future__ import annotations

# Common browser automation script templates (used as AI prompt examples)
BROWSER_EXAMPLES = """
示例 - 打开网页并搜索:
*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Search On Website
    Open Browser    https://www.example.com    Chrome
    Input Text    id=search    search query
    Click Button    id=search-button
    Wait Until Page Contains    Results
    Capture Page Screenshot    screenshot.png
    Close Browser

示例 - 登录网站:
*** Settings ***
Library    SeleniumLibrary

*** Test Cases ***
Login To Website
    Open Browser    https://www.example.com/login    Chrome
    Input Text    id=username    myuser
    Input Password    id=password    mypass
    Click Button    id=login-button
    Wait Until Page Contains    Welcome
    Close Browser
"""
