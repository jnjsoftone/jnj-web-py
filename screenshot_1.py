#!/usr/bin/env python3
import os
import sys
import asyncio
import subprocess
import time
import tempfile
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

        # 권한 확인
        self.check_permissions()

    def check_permissions(self):
        """Chrome 사용자 데이터 디렉토리 권한 확인"""
        try:
            if os.access(self.user_data_path, os.R_OK | os.W_OK):
                print("✅ Chrome 사용자 데이터 디렉토리 권한 확인 완료")
                return True
            else:
                print("⚠️  Chrome 사용자 데이터 디렉토리 권한이 부족합니다.")
                return False
        except Exception as e:
            print(f"⚠️  권한 확인 중 오류: {e}")
            return False

    def kill_existing_chrome_processes(self):
        """기존 Chrome 프로세스 종료"""
        try:
            print("🔄 기존 Chrome 프로세스를 확인합니다...")

            result = subprocess.run(
                ["pgrep", "-f", "Google Chrome"], capture_output=True, text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                print(f"   발견된 Chrome 프로세스: {len(pids)}개")

                # 자동으로 종료 (사용자 확인 생략)
                print("   🔄 기존 Chrome 프로세스를 자동으로 종료합니다...")
                for pid in pids:
                    try:
                        subprocess.run(["kill", "-TERM", pid], check=True)
                        print(f"   ✅ 프로세스 {pid} 종료 요청됨")
                    except subprocess.CalledProcessError:
                        print(f"   ⚠️  프로세스 {pid} 종료 실패")

                print("   ⏳ Chrome 종료 대기 중...")
                time.sleep(5)
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

        print(f"✅ 프로필 '{profile_name}' 확인됨: {profile_path}")
        return str(profile_path)

    def get_available_profiles(self):
        """사용 가능한 모든 프로필 목록 반환"""
        user_data = Path(self.user_data_path)
        profiles = []

        if not user_data.exists():
            return profiles

        if (user_data / "Default").exists():
            profiles.append("Default")

        for item in user_data.iterdir():
            if item.is_dir() and item.name.startswith("Profile "):
                profiles.append(item.name)

        return sorted(profiles)

    def create_temp_profile_with_data(self, source_profile):
        """임시 프로필 생성 및 데이터 복사"""
        print("📋 임시 프로필을 생성하고 데이터를 복사합니다...")

        # 임시 디렉토리 생성
        temp_dir = tempfile.mkdtemp(prefix="chrome_profile_")
        temp_profile_dir = os.path.join(temp_dir, "Default")

        source_profile_path = Path(self.user_data_path) / source_profile

        try:
            os.makedirs(temp_profile_dir, exist_ok=True)

            # 필수 파일들 복사
            essential_files = [
                "Cookies",
                "Login Data",
                "Preferences",
                "Secure Preferences",
                "Web Data",
                "History",
                "Bookmarks",
                "Local State",
            ]

            essential_dirs = [
                "Local Storage",
                "Session Storage",
                "IndexedDB",
                "databases",
            ]

            copied_count = 0

            # 파일 복사
            for file_name in essential_files:
                source_file = source_profile_path / file_name
                target_file = Path(temp_profile_dir) / file_name

                if source_file.exists():
                    try:
                        shutil.copy2(source_file, target_file)
                        copied_count += 1
                        print(f"   ✅ {file_name} 복사됨")
                    except Exception as e:
                        print(f"   ⚠️  {file_name} 복사 실패: {e}")

            # 디렉토리 복사
            for dir_name in essential_dirs:
                source_dir = source_profile_path / dir_name
                target_dir = Path(temp_profile_dir) / dir_name

                if source_dir.exists():
                    try:
                        shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
                        copied_count += 1
                        print(f"   ✅ {dir_name}/ 복사됨")
                    except Exception as e:
                        print(f"   ⚠️  {dir_name}/ 복사 실패: {e}")

            # Local State 파일을 루트에도 복사 (필요시)
            local_state_source = Path(self.user_data_path) / "Local State"
            local_state_target = Path(temp_dir) / "Local State"

            if local_state_source.exists():
                try:
                    shutil.copy2(local_state_source, local_state_target)
                    print(f"   ✅ Local State 복사됨")
                except Exception as e:
                    print(f"   ⚠️  Local State 복사 실패: {e}")

            print(f"   📊 총 {copied_count}개 항목이 복사되었습니다.")
            print(f"   📁 임시 프로필 위치: {temp_dir}")

            return temp_dir

        except Exception as e:
            print(f"   ❌ 프로필 복사 중 오류: {e}")
            # 실패 시 임시 디렉토리 정리
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except:
                pass
            raise

    async def take_screenshot_with_temp_profile(
        self, profile_name, url="https://www.naver.com", output_dir="./screenshots"
    ):
        """임시 프로필을 사용한 스크린샷"""
        profile_path = self.validate_profile(profile_name)
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_profile_name = profile_name.replace(" ", "_").replace("/", "_")
        filename = f"screenshot_{safe_profile_name}_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)

        print(f"\n🚀 임시 프로필 사용 스크린샷")
        print(f"   원본 프로필: {profile_name}")
        print(f"   URL: {url}")
        print(f"   출력 파일: {output_path}")

        # 임시 프로필 생성
        temp_profile_dir = None
        try:
            temp_profile_dir = self.create_temp_profile_with_data(profile_name)

            async with async_playwright() as p:
                print(f"🌐 Chrome을 임시 프로필과 함께 시작합니다...")

                # launch_persistent_context 사용
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=temp_profile_dir,
                    executable_path=self.chrome_executable,
                    headless=False,  # GUI 모드
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
                        "--disable-web-security",
                        "--allow-running-insecure-content",
                        "--disable-features=VizDisplayCompositor",
                        "--disable-ipc-flooding-protection",
                    ],
                    viewport={"width": 1920, "height": 1080},
                    ignore_default_args=["--enable-automation"],
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )

                # 페이지 생성 또는 기존 페이지 사용
                if context.pages:
                    page = context.pages[0]
                    print(f"   ✅ 기존 페이지 사용")
                else:
                    page = await context.new_page()
                    print(f"   ✅ 새 페이지 생성")

                # 헤더 설정
                await page.set_extra_http_headers(
                    {"Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
                )

                print(f"📄 페이지로 이동 중: {url}")

                try:
                    # 페이지 이동
                    response = await page.goto(
                        url, wait_until="domcontentloaded", timeout=30000
                    )
                    print(f"📡 응답 상태: {response.status if response else 'None'}")

                    # 추가 로딩 대기
                    print(f"⏳ 페이지 로딩 대기 중...")
                    await page.wait_for_timeout(8000)

                    # 네트워크 유휴 상태 대기
                    try:
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        print(f"✅ 네트워크 로딩 완료")
                    except:
                        print(f"⚠️  네트워크 로딩 타임아웃 (계속 진행)")

                except Exception as e:
                    print(f"⚠️  페이지 이동 실패: {e}")
                    print(f"🔄 JavaScript로 직접 이동 시도...")

                    try:
                        await page.evaluate(f'window.location.href = "{url}"')
                        await page.wait_for_timeout(10000)
                    except Exception as e2:
                        print(f"⚠️  JavaScript 이동도 실패: {e2}")

                # 현재 상태 확인
                current_url = page.url
                current_title = await page.title()
                print(f"🔍 현재 URL: {current_url}")
                print(f"📋 페이지 제목: {current_title}")

                # about:blank 체크 및 재시도
                if current_url == "about:blank" or not current_title.strip():
                    print("⚠️  페이지가 about:blank 상태입니다.")
                    print("🔄 새로고침을 시도합니다...")

                    try:
                        await page.reload(wait_until="domcontentloaded", timeout=30000)
                        await page.wait_for_timeout(5000)

                        current_url = page.url
                        current_title = await page.title()
                        print(f"🔍 새로고침 후 URL: {current_url}")
                        print(f"📋 새로고침 후 제목: {current_title}")
                    except Exception as e:
                        print(f"⚠️  새로고침 실패: {e}")

                # 로그인 상태 확인
                await self.check_login_status(page, current_url)

                print(f"📸 스크린샷 촬영 중...")

                await page.screenshot(path=output_path, full_page=True, type="png")

                print(f"✅ 스크린샷이 성공적으로 저장되었습니다!")
                print(f"   📁 파일: {output_path}")

                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"   📊 파일 크기: {file_size / 1024:.1f} KB")

                    if file_size < 10000:  # 10KB 미만
                        print(
                            f"   ⚠️  파일 크기가 작습니다. 페이지가 제대로 로드되지 않았을 수 있습니다."
                        )

                print(f"\n⏰ Chrome을 10초간 유지합니다...")
                print(f"   🔍 브라우저에서 프로필 상태를 확인해보세요!")
                print(
                    f"   📍 현재 '{profile_name}' 프로필의 데이터가 로드되어 있습니다."
                )
                await page.wait_for_timeout(10000)

                await context.close()

                return output_path

        except Exception as e:
            print(f"❌ 스크린샷 촬영 중 오류: {str(e)}")
            raise

        finally:
            # 임시 프로필 디렉토리 정리
            if temp_profile_dir and os.path.exists(temp_profile_dir):
                try:
                    shutil.rmtree(temp_profile_dir, ignore_errors=True)
                    print(f"🗑️  임시 프로필 디렉토리 정리됨: {temp_profile_dir}")
                except Exception as e:
                    print(f"⚠️  임시 디렉토리 정리 실패: {e}")

    async def check_login_status(self, page, url):
        """웹사이트별 로그인 상태 확인"""
        try:
            if "naver.com" in url:
                try:
                    # 로그인 관련 요소 확인
                    login_elements = await page.query_selector_all(
                        'a[href*="login"], .MyView-module__link_login'
                    )
                    user_elements = await page.query_selector_all(
                        '.gnb_name, [data-clk="gnb.myinfo"], .MyView-module__user_name'
                    )

                    if user_elements:
                        try:
                            user_text = await user_elements[0].text_content()
                            if user_text and user_text.strip():
                                print(
                                    f"🔐 네이버: 로그인된 상태 확인 ({user_text.strip()[:15]}...)"
                                )
                            else:
                                print("🔍 네이버: 사용자 정보 확인 실패")
                        except:
                            print("🔐 네이버: 로그인된 상태로 추정")
                    elif login_elements:
                        print("🔓 네이버: 로그인되지 않은 상태")
                    else:
                        print("🔍 네이버: 로그인 상태 불분명")

                except Exception as e:
                    print(f"🔍 네이버 로그인 상태 확인 중 오류: {e}")

            elif "google.com" in url:
                try:
                    profile_elements = await page.query_selector_all(
                        '[data-ogsr-up], .gb_d, [aria-label*="Google Account"]'
                    )
                    if profile_elements:
                        print("🔐 Google: 로그인된 상태 확인")
                    else:
                        print("🔓 Google: 로그인되지 않은 상태")
                except Exception as e:
                    print(f"🔍 Google 로그인 상태 확인 중 오류: {e}")
            else:
                print("🔍 로그인 상태 확인: 일반 웹사이트")

        except Exception as e:
            print(f"🔍 로그인 상태 확인 중 전체 오류: {e}")

    async def take_screenshot(
        self, profile_name, url="https://www.naver.com", output_dir="./screenshots"
    ):
        """메인 스크린샷 메서드"""
        self.kill_existing_chrome_processes()

        try:
            return await self.take_screenshot_with_temp_profile(
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

            display_count = min(10, len(available_profiles))
            for i, profile in enumerate(available_profiles[:display_count], 1):
                profile_path = Path(self.user_data_path) / profile
                try:
                    size = 0
                    important_files = [
                        "Cookies",
                        "Login Data",
                        "History",
                        "Preferences",
                    ]
                    for file_name in important_files:
                        file_path = profile_path / file_name
                        if file_path.exists():
                            size += file_path.stat().st_size

                    size_mb = size / (1024 * 1024)

                    login_data_exists = (profile_path / "Login Data").exists()
                    cookies_exist = (profile_path / "Cookies").exists()
                    bookmarks_exist = (profile_path / "Bookmarks").exists()

                    status = ""
                    if login_data_exists and cookies_exist and bookmarks_exist:
                        status = " 🔐📚"
                    elif login_data_exists and cookies_exist:
                        status = " 🔐"
                    elif cookies_exist:
                        status = " 🍪"

                    print(f"      {i}. {profile} ({size_mb:.1f}MB){status}")
                except:
                    print(f"      {i}. {profile} (정보 확인 실패)")

            if len(available_profiles) > display_count:
                print(f"      ... 및 {len(available_profiles) - display_count}개 더")

            print(f"\n   🔐 = 로그인 데이터, 🍪 = 쿠키, 📚 = 북마크")
        else:
            print(f"   ⚠️  사용 가능한 프로필이 없습니다.")


async def main():
    """메인 함수"""
    try:
        print("🖥️  Chrome 프로필 스크린샷 도구 (임시 프로필 방식)")
        print("=" * 60)

        screenshot_tool = ChromeProfileScreenshot()
        screenshot_tool.print_profile_info()

        if len(sys.argv) > 1:
            profile_name = sys.argv[1]
        else:
            profile_name = input(f"\n사용할 프로필 이름을 입력하세요: ").strip()

        if not profile_name:
            print("❌ 프로필 이름이 입력되지 않았습니다.")
            return

        if len(sys.argv) > 2:
            url = sys.argv[2]
        else:
            url_input = input("방문할 URL (기본값: https://www.naver.com): ").strip()
            url = url_input if url_input else "https://www.naver.com"

        print(f"\n🎯 작업 시작: Chrome 프로필 '{profile_name}' 데이터 사용")
        print(f"   📍 대상 URL: {url}")

        output_path = await screenshot_tool.take_screenshot(profile_name, url)

        print(f"\n🎉 작업 완료!")
        print(f"   📸 스크린샷: {output_path}")
        print(f"   🔍 Finder에서 열기: open {os.path.dirname(output_path)}")

        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"   📊 최종 파일 크기: {file_size / 1024 / 1024:.2f} MB")

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
        print(f"   1. Chrome이 완전히 종료되었는지 확인")
        print(f"   2. 프로필 데이터가 손상되지 않았는지 확인")
        print(f"   3. 디스크 용량이 충분한지 확인")
        print(f"   4. 다른 프로필로 테스트")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
