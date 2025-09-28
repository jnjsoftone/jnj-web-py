#!/usr/bin/env python3
import os
import sys
import asyncio
import subprocess
import time
import shutil
from pathlib import Path
from datetime import datetime

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
        self.chrome_executable = os.getenv(
            "CHROMIUM_EXECUTABLE_PATH",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )
        self.user_data_path = os.getenv(
            "CHROMIUM_USERDATA_PATH",
            "/Users/youchan/Library/Application Support/Google/Chrome",
        )

        print(f"🔧 설정 정보:")
        print(f"   Chrome 실행파일: {self.chrome_executable}")
        print(f"   사용자 데이터: {self.user_data_path}")

        # 경로 검증
        if not os.path.exists(self.chrome_executable):
            raise FileNotFoundError(
                f"Chrome 실행 파일을 찾을 수 없습니다: {self.chrome_executable}"
            )

        if not os.path.exists(self.user_data_path):
            raise FileNotFoundError(
                f"Chrome 사용자 데이터 경로를 찾을 수 없습니다: {self.user_data_path}"
            )

    def kill_existing_chrome_processes(self):
        """기존 Chrome 프로세스 종료"""
        try:
            print("🔄 기존 Chrome 프로세스를 확인합니다...")

            # Chrome 프로세스 찾기
            result = subprocess.run(
                ["pgrep", "-f", "Google Chrome"], capture_output=True, text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                print(f"   발견된 Chrome 프로세스: {len(pids)}개")

                # 사용자에게 확인
                response = (
                    input("   기존 Chrome 프로세스를 종료하시겠습니까? (y/N): ")
                    .strip()
                    .lower()
                )

                if response in ["y", "yes"]:
                    for pid in pids:
                        try:
                            subprocess.run(["kill", "-TERM", pid], check=True)
                            print(f"   ✅ 프로세스 {pid} 종료 요청됨")
                        except subprocess.CalledProcessError:
                            print(f"   ⚠️  프로세스 {pid} 종료 실패")

                    # 프로세스 종료 대기
                    print("   ⏳ Chrome 종료 대기 중...")
                    time.sleep(5)

                    # 강제 종료가 필요한지 확인
                    result2 = subprocess.run(
                        ["pgrep", "-f", "Google Chrome"], capture_output=True, text=True
                    )
                    if result2.returncode == 0 and result2.stdout.strip():
                        print("   🔨 일부 프로세스가 남아있어 강제 종료합니다...")
                        remaining_pids = result2.stdout.strip().split("\n")
                        for pid in remaining_pids:
                            try:
                                subprocess.run(["kill", "-KILL", pid], check=True)
                                print(f"   💀 프로세스 {pid} 강제 종료됨")
                            except subprocess.CalledProcessError:
                                print(f"   ⚠️  프로세스 {pid} 강제 종료 실패")
                else:
                    print("   ℹ️  기존 프로세스를 유지합니다.")
            else:
                print("   ✅ 실행 중인 Chrome 프로세스가 없습니다.")

        except Exception as e:
            print(f"   ⚠️  프로세스 확인 중 오류: {e}")

    def validate_profile(self, profile_name):
        """프로필이 존재하는지 확인"""
        profile_path = Path(self.user_data_path) / profile_name

        if not profile_path.exists():
            available_profiles = self.get_available_profiles()
            error_msg = f"프로필 '{profile_name}'을 찾을 수 없습니다."
            if available_profiles:
                error_msg += (
                    f"\n사용 가능한 프로필: {', '.join(available_profiles[:5])}"
                )
                if len(available_profiles) > 5:
                    error_msg += f" ... 및 {len(available_profiles) - 5}개 더"
            else:
                error_msg += "\n사용 가능한 프로필이 없습니다."
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

    def copy_profile_data(self, source_profile, temp_profile_dir):
        """프로필 데이터를 임시 디렉토리로 복사"""
        print(f"📋 프로필 데이터를 복사합니다...")

        source_path = Path(self.user_data_path) / source_profile
        temp_path = Path(temp_profile_dir)

        # 임시 디렉토리 생성
        temp_path.mkdir(parents=True, exist_ok=True)

        # 필수 파일들 복사
        essential_files = [
            "Cookies",
            "Login Data",
            "Preferences",
            "Secure Preferences",
            "Web Data",
            "History",
            "Bookmarks",
        ]

        essential_dirs = ["Local Storage", "Session Storage", "IndexedDB", "databases"]

        copied_files = 0

        # 파일 복사
        for file_name in essential_files:
            source_file = source_path / file_name
            if source_file.exists():
                try:
                    shutil.copy2(source_file, temp_path / file_name)
                    copied_files += 1
                    print(f"   ✅ {file_name} 복사됨")
                except Exception as e:
                    print(f"   ⚠️  {file_name} 복사 실패: {e}")

        # 디렉토리 복사
        for dir_name in essential_dirs:
            source_dir = source_path / dir_name
            if source_dir.exists():
                try:
                    shutil.copytree(
                        source_dir, temp_path / dir_name, dirs_exist_ok=True
                    )
                    copied_files += 1
                    print(f"   ✅ {dir_name}/ 복사됨")
                except Exception as e:
                    print(f"   ⚠️  {dir_name}/ 복사 실패: {e}")

        print(f"   📊 총 {copied_files}개 항목이 복사되었습니다.")
        return copied_files > 0

    async def take_screenshot_with_real_profile(
        self, profile_name, url="https://www.naver.com", output_dir="./screenshots"
    ):
        """실제 Chrome 프로필을 사용한 스크린샷"""
        profile_path = self.validate_profile(profile_name)
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_profile_name = profile_name.replace(" ", "_").replace("/", "_")
        filename = f"screenshot_{safe_profile_name}_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)

        print(f"\n🚀 실제 Chrome 프로필 사용 스크린샷")
        print(f"   프로필: {profile_name}")
        print(f"   프로필 경로: {profile_path}")
        print(f"   URL: {url}")
        print(f"   출력 파일: {output_path}")

        # 임시 사용자 데이터 디렉토리 생성
        temp_user_data = f"/tmp/chrome-profile-{timestamp}"
        temp_profile_path = os.path.join(temp_user_data, "Default")

        try:
            # 프로필 데이터 복사
            if not self.copy_profile_data(profile_name, temp_profile_path):
                print("⚠️  프로필 데이터 복사에 실패했습니다. 빈 프로필로 진행합니다.")

            async with async_playwright() as p:
                print(f"🌐 Chrome을 프로필과 함께 시작합니다...")

                # launch_persistent_context를 사용하여 프로필 로드
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=temp_user_data,
                    executable_path=self.chrome_executable,
                    headless=False,  # GUI 모드로 실행
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-background-timer-throttling",
                        "--disable-backgrounding-occluded-windows",
                        "--disable-renderer-backgrounding",
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled",
                        "--exclude-switches=enable-automation",
                        "--disable-web-security",  # CORS 문제 방지
                        "--allow-running-insecure-content",
                    ],
                    viewport={"width": 1920, "height": 1080},
                    ignore_default_args=["--enable-automation"],
                    accept_downloads=True,
                    has_touch=False,
                    is_mobile=False,
                    java_script_enabled=True,
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )

                # 기존 페이지가 있으면 사용, 없으면 새로 생성
                if context.pages:
                    page = context.pages[0]
                else:
                    page = await context.new_page()

                # User-Agent 설정
                await page.set_extra_http_headers(
                    {"Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
                )

                print(f"📄 페이지로 이동 중: {url}")

                try:
                    # 페이지 이동 (더 긴 타임아웃)
                    response = await page.goto(
                        url, wait_until="networkidle", timeout=45000
                    )
                    print(f"📡 응답 상태: {response.status if response else 'None'}")

                    if response and response.status >= 400:
                        print(f"⚠️  HTTP 오류 상태: {response.status}")

                except Exception as e:
                    print(f"⚠️  networkidle 대기 실패: {e}")
                    try:
                        # domcontentloaded로 재시도
                        response = await page.goto(
                            url, wait_until="domcontentloaded", timeout=30000
                        )
                        print(
                            f"📡 재시도 응답 상태: {response.status if response else 'None'}"
                        )
                    except Exception as e2:
                        print(f"❌ 페이지 로드 완전 실패: {e2}")
                        raise

                # 페이지 로딩 대기
                print(f"⏳ 페이지 완전 로딩 대기 중...")
                await page.wait_for_timeout(8000)

                # 현재 상태 확인
                current_url = page.url
                current_title = await page.title()
                print(f"🔍 현재 URL: {current_url}")
                print(f"📋 페이지 제목: {current_title}")

                # about:blank이거나 제목이 없으면 재시도
                if current_url == "about:blank" or not current_title.strip():
                    print(
                        "⚠️  페이지가 제대로 로드되지 않았습니다. 강제 새로고침을 시도합니다..."
                    )

                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(5000)

                        current_url = page.url
                        current_title = await page.title()
                        print(f"🔍 새로고침 후 URL: {current_url}")
                        print(f"📋 새로고침 후 제목: {current_title}")
                    except Exception as e:
                        print(f"⚠️  새로고침 실패: {e}")

                # 로그인 상태 확인 (네이버의 경우)
                if "naver.com" in current_url:
                    try:
                        # 로그인 버튼 또는 로그인된 사용자 정보 확인
                        login_elements = await page.query_selector_all(
                            'a[href*="login"], .MyView-module__link_login, .gnb_name'
                        )
                        if login_elements:
                            print("🔐 네이버 로그인 상태를 확인했습니다.")
                    except:
                        pass

                print(f"📸 스크린샷 촬영 중...")

                # 전체 페이지 스크린샷 (quality 옵션 제거)
                await page.screenshot(
                    path=output_path,
                    full_page=True,
                    type="png",
                    # quality 옵션 제거 - PNG에서는 지원되지 않음
                )

                print(f"✅ 스크린샷이 성공적으로 저장되었습니다!")
                print(f"   📁 파일: {output_path}")

                # 파일 크기 확인
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"   📊 파일 크기: {file_size / 1024:.1f} KB")

                    # 파일이 너무 작으면 경고
                    if file_size < 10000:  # 10KB 미만
                        print(
                            f"   ⚠️  파일 크기가 작습니다. 페이지가 제대로 로드되지 않았을 수 있습니다."
                        )
                else:
                    print(f"   ❌ 스크린샷 파일이 생성되지 않았습니다!")
                    raise Exception("스크린샷 파일 생성 실패")

                print(
                    f"\n⏰ Chrome 브라우저를 10초간 유지합니다 (프로필 상태 확인용)..."
                )
                print(f"   브라우저에서 로그인 상태와 프로필 정보를 확인해보세요!")
                await page.wait_for_timeout(10000)

                # 컨텍스트 종료
                await context.close()

                return output_path

        finally:
            # 임시 디렉토리 정리
            try:
                if os.path.exists(temp_user_data):
                    shutil.rmtree(temp_user_data, ignore_errors=True)
                    print(f"🗑️  임시 프로필 디렉토리 정리됨: {temp_user_data}")
            except Exception as e:
                print(f"⚠️  임시 디렉토리 정리 실패: {e}")

    async def take_screenshot(
        self, profile_name, url="https://www.naver.com", output_dir="./screenshots"
    ):
        """메인 스크린샷 메서드"""

        # 기존 Chrome 프로세스 확인
        self.kill_existing_chrome_processes()

        try:
            return await self.take_screenshot_with_real_profile(
                profile_name, url, output_dir
            )
        except Exception as e:
            print(f"❌ 프로필 스크린샷 실패: {str(e)}")
            raise

    def print_profile_info(self):
        """사용 가능한 프로필 정보 출력"""
        print("\n📁 Chrome 프로필 정보:")
        print(f"   📂 경로: {self.user_data_path}")

        available_profiles = self.get_available_profiles()
        if available_profiles:
            print(f"   📋 사용 가능한 프로필: {len(available_profiles)}개")

            # 처음 10개만 표시
            display_count = min(10, len(available_profiles))
            for i, profile in enumerate(available_profiles[:display_count], 1):
                profile_path = Path(self.user_data_path) / profile
                try:
                    # 프로필 크기 계산 (빠른 계산을 위해 주요 파일들만)
                    size = 0
                    for file_name in [
                        "Cookies",
                        "Login Data",
                        "History",
                        "Preferences",
                    ]:
                        file_path = profile_path / file_name
                        if file_path.exists():
                            size += file_path.stat().st_size

                    size_mb = size / (1024 * 1024)

                    # 로그인 데이터 확인
                    login_data_exists = (profile_path / "Login Data").exists()
                    cookies_exist = (profile_path / "Cookies").exists()

                    status = ""
                    if login_data_exists and cookies_exist:
                        status = " 🔐"
                    elif cookies_exist:
                        status = " 🍪"

                    print(f"      {i}. {profile} ({size_mb:.1f}MB){status}")
                except Exception as e:
                    print(f"      {i}. {profile} (크기 확인 실패)")

            if len(available_profiles) > display_count:
                print(f"      ... 및 {len(available_profiles) - display_count}개 더")

            print(f"\n   🔐 = 로그인 데이터 있음, 🍪 = 쿠키만 있음")
        else:
            print(f"   ⚠️  사용 가능한 프로필이 없습니다.")


async def main():
    """메인 함수"""
    try:
        print("🖥️  Chrome 프로필 스크린샷 도구 (실제 프로필 사용)")
        print("=" * 60)

        screenshot_tool = ChromeProfileScreenshot()
        screenshot_tool.print_profile_info()

        # 프로필 이름 입력받기
        if len(sys.argv) > 1:
            profile_name = sys.argv[1]
        else:
            profile_name = input(f"\n사용할 프로필 이름을 입력하세요: ").strip()

        if not profile_name:
            print("❌ 프로필 이름이 입력되지 않았습니다.")
            return

        # URL 입력받기
        if len(sys.argv) > 2:
            url = sys.argv[2]
        else:
            url_input = input("방문할 URL (기본값: https://www.naver.com): ").strip()
            url = url_input if url_input else "https://www.naver.com"

        print(f"\n🎯 작업 시작: Chrome 프로필 '{profile_name}' 사용")
        print(f"   📍 대상 URL: {url}")

        # 스크린샷 촬영
        output_path = await screenshot_tool.take_screenshot(profile_name, url)

        print(f"\n🎉 작업 완료!")
        print(f"   📸 스크린샷: {output_path}")
        print(f"   🔍 Finder에서 열기: open {os.path.dirname(output_path)}")

        # 추가 정보
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"   📊 최종 파일 크기: {file_size / 1024 / 1024:.2f} MB")

            # 이미지 미리보기 (macOS)
            try:
                subprocess.run(["open", "-a", "Preview", output_path], check=False)
                print(f"   👁️  Preview 앱으로 이미지를 열었습니다.")
            except:
                pass

    except KeyboardInterrupt:
        print("\n\n⏹️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 최종 오류: {str(e)}")
        print(f"\n🔧 해결 방법:")
        print(f"   1. Chrome을 완전히 종료한 후 재시도")
        print(f"   2. 네트워크 연결 확인")
        print(f"   3. 프로필 이름 확인 (대소문자 정확히)")
        print(f"   4. 다른 URL로 테스트 (예: https://www.google.com)")
        print(f"   5. screenshots 디렉토리 권한 확인")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
