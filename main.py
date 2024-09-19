import copy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from z3 import *


def init_board(rows, cols):
    board = [[None for _ in range(cols)] for _ in range(rows)]
    return board


def click_tile(row, col):
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                f".game-row:nth-of-type({row+1}) .single-element:nth-of-type({col+1})",
            )
        )
    ).click()
    flood_fill(row, col)


def flood_fill(row, col):
    def fill(row, col):
        if not inside(row, col):
            return
        if board[row][col] != None:
            if (row, col) in border_tiles:
                border_tiles.remove((row, col))
            return
        if "opened-div" not in WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    f".game-row:nth-of-type({row+1}) .single-element:nth-of-type({col+1})",
                )
            )
        ).get_attribute("class"):
            border_tiles.add((row, col))
            return
        text = (
            WebDriverWait(driver, 10)
            .until(
                EC.presence_of_element_located(
                    (
                        By.CSS_SELECTOR,
                        f".game-row:nth-of-type({row+1}) .single-element:nth-of-type({col+1})",
                    )
                )
            )
            .get_attribute("innerText")
        )
        board[row][col] = int(text) if text.isdigit() else 0
        if board[row][col] > 0:
            unsolved_tiles.add((row, col))
        fill(row - 1, col - 1)
        fill(row - 1, col)
        fill(row - 1, col + 1)
        fill(row, col - 1)
        fill(row, col + 1)
        fill(row + 1, col - 1)
        fill(row + 1, col)
        fill(row + 1, col + 1)

    fill(row, col)


def inside(row, col):
    return row >= 0 and row < rows and col >= 0 and col < cols


def neighbours(row, col):
    return [
        (i, j)
        for i in range(max(0, row - 1), min(row + 2, rows))
        for j in range(max(0, col - 1), min(col + 2, cols))
        if (i, j) != (row, col)
    ]


def neighbours_hidden(row, col):
    return [
        tile
        for tile in neighbours(row, col)
        if board[tile[0]][tile[1]] == None or board[tile[0]][tile[1]] == -1
    ]


def neighbours_unsure(row, col):
    return [tile for tile in neighbours(row, col) if board[tile[0]][tile[1]] == None]


def neighbours_unsafe(row, col):
    return [tile for tile in neighbours(row, col) if board[tile[0]][tile[1]] == -1]


def chk_bomb(row, col):
    s = Solver()
    cells = [
        [Int("r%d_c%d" % (r, c)) for c in range(cols + 2)] for r in range(rows + 2)
    ]
    for c in range(cols + 2):
        s.add(cells[0][c] == 0)
        s.add(cells[rows + 1][c] == 0)
    for r in range(rows + 2):
        s.add(cells[r][0] == 0)
        s.add(cells[r][cols + 1] == 0)
    for r in range(1, rows + 1):
        for c in range(1, cols + 1):
            s.add(Or(cells[r][c] == 0, cells[r][c] == 1))
            t = board[r - 1][c - 1]
            if isinstance(t, int) and t >= 0:
                s.add(cells[r][c] == 0)
                expr = (
                    cells[r - 1][c - 1]
                    + cells[r - 1][c]
                    + cells[r - 1][c + 1]
                    + cells[r][c - 1]
                    + cells[r][c + 1]
                    + cells[r + 1][c - 1]
                    + cells[r + 1][c]
                    + cells[r + 1][c + 1]
                    == t
                )
            s.add(expr)
    for r, c in unsafe_tiles:
        s.add(cells[r + 1][c + 1] == 1)
    s.add(cells[row][col] == 1)
    if s.check() == unsat:
        click_tile(row - 1, col - 1)


if __name__ == "__main__":
    chrome_options = Options()
    chrome_options.add_experimental_option("detach", True)

    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://minesweepertmu.web.app/")

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                f".menu-size",
            )
        )
    ).click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                f"#radio__mid",
            )
        )
    ).click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (
                By.CSS_SELECTOR,
                f".new-box-button",
            )
        )
    ).click()

    rows, cols = 16, 16
    board = init_board(rows, cols)
    ex_board = copy.deepcopy(board)
    border_tiles = set()
    unsafe_tiles = set()
    unsolved_tiles = set()

    click_tile(0, 0)

    while ex_board != board:
        ex_board = copy.deepcopy(board)

        for row, col in unsolved_tiles.copy():
            neighbours_hidden_list = neighbours_hidden(row, col)
            if board[row][col] == len(neighbours_hidden_list):
                for tile in neighbours_hidden_list:
                    board[tile[0]][tile[1]] = -1
                    unsafe_tiles.add((*tile,))
                    if (row, col) in unsolved_tiles:
                        unsolved_tiles.remove((row, col))

        for row, col in unsolved_tiles.copy():
            if board[row][col] == len(neighbours_unsafe(row, col)):
                for tile in neighbours_unsure(row, col):
                    click_tile(*tile)
                    if (row, col) in unsolved_tiles:
                        unsolved_tiles.remove((row, col))

        if ex_board == board:
            for r, c in border_tiles.copy():
                chk_bomb(r + 1, c + 1)
