# todo.py
from pathlib import Path
from typing import Dict, List

import csv
from fastapi import APIRouter, FastAPI, HTTPException

CSV_PATH = Path('todo_list.csv')

app = FastAPI(title='Simple TODO API')
router = APIRouter()

# 메모리 상의 리스트
# 프로그램 시작 시 CSV에서 읽어서 여기 넣고,
# 새로 추가되면 CSV에도 다시 저장한다.
todo_list: List[Dict[str, str]] = []


def init_csv_file() -> None:
    """CSV 파일이 없으면 헤더를 만들어둔다."""
    if not CSV_PATH.exists():
        with CSV_PATH.open('w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=['id', 'content'])
            writer.writeheader()


def load_todo_list() -> None:
    """CSV에서 todo_list로 데이터를 읽어온다."""
    if not CSV_PATH.exists():
        init_csv_file()
        return

    with CSV_PATH.open('r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        todo_list.clear()
        for row in reader:
            # CSV에 저장된 건 전부 문자열이므로 그대로 둔다.
            todo_list.append({'id': row['id'], 'content': row['content']})


def save_todo_list() -> None:
    """현재 메모리의 todo_list를 CSV로 다시 저장한다."""
    with CSV_PATH.open('w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['id', 'content'])
        writer.writeheader()
        for item in todo_list:
            writer.writerow(item)


def get_next_id() -> str:
    """다음 사용할 id를 문자열로 돌려준다."""
    if not todo_list:
        return '1'
    # 마지막 id + 1
    last_id = max(int(item['id']) for item in todo_list)
    return str(last_id + 1)


@router.post('/todo')
async def add_todo(payload: Dict) -> Dict:
    """
    todo_list에 새로운 항목을 추가한다.
    - POST 방식
    - 입력/출력은 Dict
    - 보너스: 빈 dict가 들어오면 경고
    """
    if not payload:
        # 보너스 과제: 빈 값이면 경고
        raise HTTPException(status_code=400, detail='입력 데이터가 비어 있습니다.')

    # 과제에서 Dict 타입이라고 했으니 단순하게 content만 받는 형태로 간다.
    # {"content": "할 일"} 이런 식.
    content = payload.get('content')
    if not content:
        raise HTTPException(status_code=400, detail='content 필드는 필수입니다.')

    new_item = {
        'id': get_next_id(),
        'content': content,
    }
    todo_list.append(new_item)
    save_todo_list()
    return {'message': 'todo가 추가되었습니다.', 'data': new_item}


@router.get('/todo')
async def retrieve_todo() -> Dict:
    """
    todo_list 전체를 Dict로 돌려준다.
    - GET 방식
    - 출력은 Dict
    """
    return {'count': len(todo_list), 'data': todo_list}


# 라우터를 앱에 등록
app.include_router(router)


# 앱 시작 시 CSV 로드
@app.on_event('startup')
async def startup_event() -> None:
    init_csv_file()
    load_todo_list()
