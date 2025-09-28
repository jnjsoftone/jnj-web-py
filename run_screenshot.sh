#!/bin/bash
# run_screenshot.sh

# 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "🔄 가상환경을 활성화합니다..."
    source venv/bin/activate
fi

# Python 스크립트 실행
python3 screenshot.py "$@"
