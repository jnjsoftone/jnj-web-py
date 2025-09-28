"""
CHROMIUM_EXECUTABLE_PATH, CHROMIUM_USERDATA_PATH 환경변수는 아래와 같이 설정되어 있어요.

export CHROMIUM_EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
export CHROMIUM_USERDATA_PATH="/Users/youchan/Library/Application Support/Google/Chrome"

'Profile 39' 와 같이 프로필을 입력받으면 'Profile 39'로 시스템에 설치된 크롬 브라우저가 열리도록 하고, https://www.naver.com 에 방문하여 테스트로 스크린샷을 찍어 저장하는 python 코드를 만들어주세요.
"""

macOS에서 `externally-managed-environment` 오류가 발생했군요! 이는 시스템 Python 환경을 보호하기 위한 정책입니다. 가상환경을 사용해서 해결해보겠습니다.

## 1. 가상환경 생성 및 활성화

```bash
# 현재 디렉토리에 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# 가상환경이 활성화되면 프롬프트 앞에 (venv)가 표시됩니다
```

## 2. Playwright 설치

```bash
# 가상환경에서 playwright 설치
pip install playwright

# 필요시 다른 의존성도 설치
pip install asyncio pathlib
```

## 3. 수정된 Python 코드 (가상환경용)

```python
#!/usr/bin/env python3
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Playwright 가져오기 전에 경로 확인
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright가 설치되지 않았습니다.")
    print("가상환경을 활성화하고 다음 명령을 실행하세요:")
    print("  source venv/bin/activate")
    print("  pip install playwright")
    sys.exit(1)

class ChromeProfileScreenshot:
    def __init__(self):
        # 환경변수에서 Chrome 경로 가져오기
        self.chrome_executable = os.getenv('CHROMIUM_EXECUTABLE_PATH',
                                         '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        self.user_data_path = os.getenv('CHROMIUM_USERDATA_PATH',
                                      '/Users/youchan/Library/Application Support/Google/Chrome')

        print(f"🔧 설정 정보:")
        print(f"   Chrome 실행파일: {self.chrome_executable}")
        print(f"   사용자 데이터: {self.user_data_path}")

        # 경로 검증
        if not os.path.exists(self.chrome_executable):
            raise FileNotFoundError(f"Chrome 실행 파일을 찾을 수 없습니다: {self.chrome_executable}")

        if not os.path.exists(self.user_data_path):
            raise FileNotFoundError(f"Chrome 사용자 데이터 경로를 찾을 수 없습니다: {self.user_data_path}")

    def validate_profile(self, profile_name):
        """프로필이 존재하는지 확인"""
        profile_path = Path(self.user_data_path) / profile_name

        if not profile_path.exists():
            # 사용 가능한 프로필 목록 표시
            available_profiles = self.get_available_profiles()
            error_msg = f"프로필 '{profile_name}'을 찾을 수 없습니다."
            if available_profiles:
                error_msg += f"\n사용 가능한 프로필: {', '.join(available_profiles)}"
            else:
                error_msg += "\n사용 가능한 프로필이 없습니다. Chrome을 먼저 실행해주세요."
            raise ValueError(error_msg)

        return str(profile_path)

    def get_available_profiles(self):
        """사용 가능한 모든 프로필 목록 반환"""
        user_data = Path(self.user_data_path)
        profiles = []

        if not user_data.exists():
            return profiles

        # Default 프로필 확인
        if (user_data / "Default").exists():
            profiles.append("Default")

        # Profile X 형태의 프로필들 확인
        for item in user_data.iterdir():
            if item.is_dir() and item.name.startswith("Profile "):
                profiles.append(item.name)

        return sorted(profiles)

    async def take_screenshot(self, profile_name, url="https://www.naver.com", output_dir="./screenshots"):
        """지정된 프로필로 Chrome을 열고 스크린샷 촬영"""

        # 프로필 검증
        profile_path = self.validate_profile(profile_name)

        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)

        # 스크린샷 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_profile_name = profile_name.replace(' ', '_').replace('/', '_')
        filename = f"screenshot_{safe_profile_name}_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)

        print(f"\n🚀 Chrome 실행 설정:")
        print(f"   프로필: {profile_name}")
        print(f"   URL: {url}")
        print(f"   출력 파일: {output_path}")

        async with async_playwright() as p:
            try:
                # Chrome을 영구 컨텍스트로 시작 (프로필 사용)
                print(f"🌐 Chrome 브라우저를 시작합니다...")

                context = await p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_path,
                    executable_path=self.chrome_executable,
                    headless=False,  # GUI로 Chrome 열기
                    args=[
                        f'--profile-directory={profile_name}',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding',
                        '--disable-blink-features=AutomationControlled',  # 자동화 감지 방지
                        '--exclude-switches=enable-automation',
                        '--disable-extensions-except',
                        '--disable-plugins-discovery'
                    ],
                    viewport={'width': 1920, 'height': 1080},
                    ignore_default_args=['--enable-automation'],
                    slow_mo=1000  # 동작을 1초씩 느리게 (시각적 확인용)
                )

                # 새 페이지 생성 또는 기존 페이지 사용
                if context.pages:
                    page = context.pages[0]
                else:
                    page = await context.new_page()

                print(f"📄 페이지로 이동 중: {url}")

                # 페이지 이동
                await page.goto(url, wait_until='networkidle', timeout=30000)

                # 페이지 로딩 완료 대기
                print(f"⏳ 페이지 로딩 완료 대기 중...")
                await page.wait_for_timeout(3000)

                print(f"📸 스크린샷 촬영 중...")

                # 전체 페이지 스크린샷 촬영
                await page.screenshot(
                    path=output_path,
                    full_page=True,
                    type='png'
                )

                print(f"✅ 스크린샷이 성공적으로 저장되었습니다!")
                print(f"   파일: {output_path}")

                # 페이지 제목 확인
                title = await page.title()
                print(f"📋 페이지 제목: {title}")

                # 파일 크기 확인
                file_size = os.path.getsize(output_path)
                print(f"📊 파일 크기: {file_size / 1024:.1f} KB")

                # 잠시 대기 (사용자가 브라우저를 확인할 수 있도록)
                print(f"\n⏰ 5초 후 브라우저를 닫습니다...")
                await page.wait_for_timeout(5000)

                # 컨텍스트 종료
                await context.close()

                return output_path

            except Exception as e:
                print(f"❌ 오류 발생: {str(e)}")
                print(f"🔍 디버그 정보:")
                print(f"   Chrome 실행파일 존재: {os.path.exists(self.chrome_executable)}")
                print(f"   사용자 데이터 존재: {os.path.exists(self.user_data_path)}")
                print(f"   프로필 경로 존재: {os.path.exists(profile_path)}")
                raise

    def print_profile_info(self):
        """사용 가능한 프로필 정보 출력"""
        print("\n📁 Chrome 프로필 정보:")
        print(f"   📂 경로: {self.user_data_path}")

        available_profiles = self.get_available_profiles()
        if available_profiles:
            print(f"   📋 사용 가능한 프로필: {len(available_profiles)}개")

            for i, profile in enumerate(available_profiles, 1):
                profile_path = Path(self.user_data_path) / profile

                # 프로필 크기 계산
                try:
                    size = sum(f.stat().st_size for f in profile_path.rglob('*') if f.is_file())
                    size_mb = size / (1024 * 1024)
                    print(f"      {i}. {profile} ({size_mb:.1f}MB)")
                except:
                    print(f"      {i}. {profile}")
        else:
            print(f"   ⚠️  사용 가능한 프로필이 없습니다.")
            print(f"      Chrome을 먼저 실행하여 프로필을 생성해주세요.")

async def main():
    """메인 함수"""
    try:
        print("🖥️  Chrome 프로필 스크린샷 도구")
        print("=" * 50)

        screenshot_tool = ChromeProfileScreenshot()

        # 프로필 정보 출력
        screenshot_tool.print_profile_info()

        # 프로필 이름 입력받기
        if len(sys.argv) > 1:
            profile_name = sys.argv[1]
        else:
            print(f"\n사용법 예시:")
            print(f"  python {sys.argv[0]} 'Profile 39'")
            print(f"  python {sys.argv[0]} 'Profile 39' 'https://www.google.com'")
            profile_name = input(f"\n사용할 프로필 이름을 입력하세요: ").strip()

        if not profile_name:
            print("❌ 프로필 이름이 입력되지 않았습니다.")
            return

        # URL 입력받기 (선택사항)
        if len(sys.argv) > 2:
            url = sys.argv[2]
        else:
            url_input = input("방문할 URL (기본값: https://www.naver.com): ").strip()
            url = url_input if url_input else "https://www.naver.com"

        print(f"\n🎯 작업 시작: Chrome 프로필 '{profile_name}' 사용")

        # 스크린샷 촬영
        output_path = await screenshot_tool.take_screenshot(profile_name, url)

        print(f"\n🎉 작업 완료!")
        print(f"   📸 스크린샷: {output_path}")
        print(f"   🔍 Finder에서 열기: open {os.path.dirname(output_path)}")

    except KeyboardInterrupt:
        print("\n\n⏹️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류: {str(e)}")
        print(f"\n🔧 해결 방법:")
        print(f"   1. Chrome이 설치되어 있는지 확인")
        print(f"   2. 환경변수가 올바르게 설정되어 있는지 확인")
        print(f"   3. 지정한 프로필이 존재하는지 확인")
        sys.exit(1)

if __name__ == "__main__":
    # asyncio 이벤트 루프 실행
    asyncio.run(main())
```

## 4. 실행 스크립트 생성

**`run_screenshot.sh` 파일 생성:**

```bash
#!/bin/bash
# run_screenshot.sh

# 가상환경 활성화 확인
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "🔄 가상환경을 활성화합니다..."
    source venv/bin/activate
fi

# Python 스크립트 실행
python3 screenshot.py "$@"
```

**실행 권한 부여:**

```bash
chmod +x run_screenshot.sh
```

## 5. 사용 방법

**1단계: 가상환경 설정 (최초 1회만)**

```bash
# 가상환경 생성
python3 -m venv venv

# 가상환경 활성화
source venv/bin/activate

# Playwright 설치
pip install playwright

# requirements.txt 생성 (선택사항)
pip freeze > requirements.txt
```

**2단계: 스크립트 실행**

```bash
# 방법 1: 가상환경 직접 활성화
source venv/bin/activate
python3 screenshot.py "Profile 39"

# 방법 2: 실행 스크립트 사용
./run_screenshot.sh "Profile 39"

# 방법 3: URL도 함께 지정
./run_screenshot.sh "Profile 39" "https://www.google.com"
```

## 6. 대안 방법 (pipx 사용)

```bash
# pipx 설치 (Homebrew)
brew install pipx

# pipx로 playwright 설치
pipx install playwright
pipx inject playwright asyncio

# 스크립트 실행
python3 screenshot.py "Profile 39"
```

이제 가상환경에서 Playwright를 사용하여 Chrome 프로필 스크린샷을 촬영할 수 있습니다!

=======

macOS 환경에서 시스템 Chrome을 사용하여 특정 프로필로 스크린샷을 찍는 Python 코드를 만들어드리겠습니다.

```python
#!/usr/bin/env python3
import os
import sys
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from datetime import datetime

class ChromeProfileScreenshot:
    def __init__(self):
        # 환경변수에서 Chrome 경로 가져오기
        self.chrome_executable = os.getenv('CHROMIUM_EXECUTABLE_PATH',
                                         '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        self.user_data_path = os.getenv('CHROMIUM_USERDATA_PATH',
                                      '/Users/youchan/Library/Application Support/Google/Chrome')

        # 경로 검증
        if not os.path.exists(self.chrome_executable):
            raise FileNotFoundError(f"Chrome 실행 파일을 찾을 수 없습니다: {self.chrome_executable}")

        if not os.path.exists(self.user_data_path):
            raise FileNotFoundError(f"Chrome 사용자 데이터 경로를 찾을 수 없습니다: {self.user_data_path}")

    def validate_profile(self, profile_name):
        """프로필이 존재하는지 확인"""
        profile_path = Path(self.user_data_path) / profile_name

        if not profile_path.exists():
            # 사용 가능한 프로필 목록 표시
            available_profiles = self.get_available_profiles()
            raise ValueError(f"프로필 '{profile_name}'을 찾을 수 없습니다.\n"
                           f"사용 가능한 프로필: {available_profiles}")

        return str(profile_path)

    def get_available_profiles(self):
        """사용 가능한 모든 프로필 목록 반환"""
        user_data = Path(self.user_data_path)
        profiles = []

        # Default 프로필 확인
        if (user_data / "Default").exists():
            profiles.append("Default")

        # Profile X 형태의 프로필들 확인
        for item in user_data.iterdir():
            if item.is_dir() and item.name.startswith("Profile "):
                profiles.append(item.name)

        return profiles

    async def take_screenshot(self, profile_name, url="https://www.naver.com", output_dir="./screenshots"):
        """지정된 프로필로 Chrome을 열고 스크린샷 촬영"""

        # 프로필 검증
        profile_path = self.validate_profile(profile_name)

        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)

        # 스크린샷 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{profile_name.replace(' ', '_')}_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)

        print(f"Chrome 설정:")
        print(f"  - 실행 파일: {self.chrome_executable}")
        print(f"  - 사용자 데이터: {self.user_data_path}")
        print(f"  - 프로필: {profile_name}")
        print(f"  - URL: {url}")
        print(f"  - 출력 파일: {output_path}")

        async with async_playwright() as p:
            try:
                # Chrome을 영구 컨텍스트로 시작 (프로필 사용)
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_path,
                    executable_path=self.chrome_executable,
                    headless=False,  # GUI로 Chrome 열기
                    args=[
                        f'--profile-directory={profile_name}',
                        '--no-first-run',
                        '--no-default-browser-check',
                        '--disable-background-timer-throttling',
                        '--disable-backgrounding-occluded-windows',
                        '--disable-renderer-backgrounding'
                    ],
                    viewport={'width': 1920, 'height': 1080},
                    ignore_default_args=['--enable-automation']  # "Chrome이 자동화된 테스트 소프트웨어에 의해 제어되고 있습니다" 메시지 제거
                )

                # 새 페이지 생성 또는 기존 페이지 사용
                if context.pages:
                    page = context.pages[0]
                else:
                    page = await context.new_page()

                print(f"\n네이버 페이지로 이동 중...")

                # 페이지 이동
                await page.goto(url, wait_until='networkidle', timeout=30000)

                # 페이지 로딩 완료 대기
                await page.wait_for_timeout(3000)

                print(f"스크린샷 촬영 중...")

                # 전체 페이지 스크린샷 촬영
                await page.screenshot(
                    path=output_path,
                    full_page=True,
                    type='png'
                )

                print(f"✅ 스크린샷이 성공적으로 저장되었습니다: {output_path}")

                # 페이지 제목 확인
                title = await page.title()
                print(f"📄 페이지 제목: {title}")

                # 잠시 대기 (사용자가 브라우저를 확인할 수 있도록)
                print(f"\n5초 후 브라우저를 닫습니다...")
                await page.wait_for_timeout(5000)

                # 컨텍스트 종료
                await context.close()

                return output_path

            except Exception as e:
                print(f"❌ 오류 발생: {str(e)}")
                raise

    def print_profile_info(self):
        """사용 가능한 프로필 정보 출력"""
        print("📁 Chrome 프로필 정보:")
        print(f"   경로: {self.user_data_path}")

        available_profiles = self.get_available_profiles()
        print(f"   사용 가능한 프로필: {len(available_profiles)}개")

        for i, profile in enumerate(available_profiles, 1):
            profile_path = Path(self.user_data_path) / profile

            # 프로필 크기 계산
            try:
                size = sum(f.stat().st_size for f in profile_path.rglob('*') if f.is_file())
                size_mb = size / (1024 * 1024)
                print(f"   {i}. {profile} ({size_mb:.1f}MB)")
            except:
                print(f"   {i}. {profile}")

async def main():
    """메인 함수"""
    try:
        screenshot_tool = ChromeProfileScreenshot()

        # 프로필 정보 출력
        screenshot_tool.print_profile_info()

        # 프로필 이름 입력받기
        if len(sys.argv) > 1:
            profile_name = sys.argv[1]
        else:
            profile_name = input("\n사용할 프로필 이름을 입력하세요 (예: 'Profile 39'): ").strip()

        if not profile_name:
            print("❌ 프로필 이름이 입력되지 않았습니다.")
            return

        # URL 입력받기 (선택사항)
        if len(sys.argv) > 2:
            url = sys.argv[2]
        else:
            url_input = input("방문할 URL을 입력하세요 (기본값: https://www.naver.com): ").strip()
            url = url_input if url_input else "https://www.naver.com"

        print(f"\n🚀 Chrome 프로필 '{profile_name}'으로 스크린샷을 촬영합니다...")

        # 스크린샷 촬영
        output_path = await screenshot_tool.take_screenshot(profile_name, url)

        print(f"\n✨ 작업 완료!")
        print(f"   스크린샷: {output_path}")

    except KeyboardInterrupt:
        print("\n\n⏹️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    # 사용 예시 출력
    if len(sys.argv) == 1:
        print("🖥️  Chrome 프로필 스크린샷 도구")
        print("=" * 50)
        print("사용법:")
        print("  python screenshot.py [프로필명] [URL]")
        print("  python screenshot.py 'Profile 39'")
        print("  python screenshot.py 'Profile 39' 'https://www.google.com'")
        print("")

    # Playwright 실행
    asyncio.run(main())
```

**추가로 필요한 의존성 설치:**

```bash
# Playwright 설치
pip install playwright

# Playwright 브라우저 설치 (선택사항 - 시스템 Chrome 사용하므로 불필요)
# playwright install chromium
```

**사용 방법:**

1. **대화형 실행:**

```bash
python screenshot.py
```

2. **명령행 인수로 실행:**

```bash
# 프로필만 지정
python screenshot.py "Profile 39"

# 프로필과 URL 모두 지정
python screenshot.py "Profile 39" "https://www.google.com"
```

**주요 기능:**

1. **환경변수 사용**: `CHROMIUM_EXECUTABLE_PATH`와 `CHROMIUM_USERDATA_PATH` 환경변수 자동 인식
2. **프로필 검증**: 지정된 프로필이 존재하는지 확인
3. **사용 가능한 프로필 목록**: 시스템에 있는 모든 Chrome 프로필 표시
4. **GUI Chrome 실행**: headless=False로 실제 Chrome 브라우저 창 열기
5. **전체 페이지 스크린샷**: full_page=True로 전체 페이지 캡처
6. **자동 파일명 생성**: 프로필명과 타임스탬프 포함
7. **에러 처리**: 상세한 오류 메시지와 복구 가이드

**출력 파일 예시:**

```
screenshots/screenshot_Profile_39_20241228_143052.png
```

이 코드는 macOS 환경에서 시스템에 설치된 Chrome의 특정 프로필을 사용하여 웹페이지 스크린샷을 촬영하는 완전한 솔루션입니다.
