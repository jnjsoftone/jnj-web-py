#!/usr/bin/env python3
import os
import sys
import asyncio
import subprocess
import time
import json
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

                    print("   ⏳ Chrome 종료 대기 중...")
                    time.sleep(5)
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

    def load_profile_cookies(self, profile_name):
        """프로필의 쿠키 데이터 로드"""
        try:
            profile_path = Path(self.user_data_path) / profile_name
            cookies_file = profile_path / "Cookies"

            if cookies_file.exists():
                print(f"✅ 프로필 쿠키 파일 발견: {cookies_file}")
                return True
            else:
                print(f"⚠️  프로필 쿠키 파일 없음: {cookies_file}")
                return False
        except Exception as e:
            print(f"⚠️  쿠키 로드 중 오류: {e}")
            return False

    async def take_screenshot_with_launch(
        self, profile_name, url="https://www.naver.com", output_dir="./screenshots"
    ):
        """launch 방식으로 프로필 사용 스크린샷"""
        profile_path = self.validate_profile(profile_name)
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_profile_name = profile_name.replace(" ", "_").replace("/", "_")
        filename = f"screenshot_{safe_profile_name}_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)

        print(f"\n🚀 Chrome launch 방식으로 프로필 사용")
        print(f"   프로필: {profile_name}")
        print(f"   URL: {url}")
        print(f"   출력 파일: {output_path}")

        # 쿠키 상태 확인
        self.load_profile_cookies(profile_name)

        async with async_playwright() as p:
            try:
                print(f"🌐 Chrome 브라우저를 시작합니다...")

                browser = await p.chromium.launch(
                    executable_path=self.chrome_executable,
                    headless=False,
                    args=[
                        f"--user-data-dir={self.user_data_path}",
                        f"--profile-directory={profile_name}",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--start-maximized",
                        "--disable-blink-features=AutomationControlled",
                        "--exclude-switches=enable-automation",
                        "--disable-web-security",
                        "--allow-running-insecure-content",
                        "--disable-features=VizDisplayCompositor",
                    ],
                )

                # 새 컨텍스트 생성 (빈 컨텍스트)
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    locale="ko-KR",
                    timezone_id="Asia/Seoul",
                )

                page = await context.new_page()

                # 추가 헤더 설정
                await page.set_extra_http_headers(
                    {
                        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    }
                )

                print(f"📄 페이지로 이동 중: {url}")

                # 페이지 이동 시도
                try:
                    response = await page.goto(
                        url, wait_until="domcontentloaded", timeout=30000
                    )
                    print(f"📡 응답 상태: {response.status if response else 'None'}")

                    # 추가 로딩 대기
                    print(f"⏳ 페이지 로딩 대기 중...")
                    await page.wait_for_timeout(5000)

                    # JavaScript 실행 대기
                    try:
                        await page.wait_for_function(
                            'document.readyState === "complete"', timeout=10000
                        )
                        print(f"✅ 페이지 로딩 완료")
                    except:
                        print(f"⚠️  페이지 완전 로딩 타임아웃 (계속 진행)")

                except Exception as e:
                    print(f"⚠️  페이지 이동 실패: {e}")

                    # 직접 URL 이동 시도
                    print(f"🔄 JavaScript로 직접 이동 시도...")
                    try:
                        await page.evaluate(f'window.location.href = "{url}"')
                        await page.wait_for_timeout(8000)
                    except Exception as e2:
                        print(f"⚠️  JavaScript 이동도 실패: {e2}")

                # 현재 상태 확인
                current_url = page.url
                current_title = await page.title()
                print(f"🔍 현재 URL: {current_url}")
                print(f"📋 페이지 제목: {current_title}")

                # about:blank 체크 및 재시도
                if current_url == "about:blank" or not current_title.strip():
                    print("⚠️  여전히 about:blank 상태입니다. 강제 이동을 시도합니다...")

                    # 여러 방법으로 시도
                    methods = [
                        f'window.location.replace("{url}")',
                        f'window.location.assign("{url}")',
                        f'window.open("{url}", "_self")',
                    ]

                    for i, method in enumerate(methods, 1):
                        try:
                            print(f"   방법 {i}: {method}")
                            await page.evaluate(method)
                            await page.wait_for_timeout(5000)

                            current_url = page.url
                            current_title = await page.title()
                            print(f"   결과 URL: {current_url}")
                            print(f"   결과 제목: {current_title}")

                            if current_url != "about:blank" and current_title.strip():
                                print(f"   ✅ 방법 {i} 성공!")
                                break
                        except Exception as e:
                            print(f"   ❌ 방법 {i} 실패: {e}")

                # 최종 상태 확인
                current_url = page.url
                current_title = await page.title()

                if current_url == "about:blank":
                    print("⚠️  모든 시도 후에도 about:blank 상태입니다.")
                    print("   하지만 스크린샷은 촬영합니다...")

                # 로그인 상태 확인
                await self.check_login_status(page, current_url)

                print(f"📸 스크린샷 촬영 중...")

                await page.screenshot(path=output_path, full_page=True, type="png")

                print(f"✅ 스크린샷이 성공적으로 저장되었습니다!")
                print(f"   📁 파일: {output_path}")

                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"   📊 파일 크기: {file_size / 1024:.1f} KB")

                print(f"\n⏰ Chrome 브라우저를 10초간 유지합니다...")
                print(f"   현재 상태를 확인해보세요. 프로필이 제대로 로드되었나요?")
                await page.wait_for_timeout(10000)

                await context.close()
                await browser.close()

                return output_path

            except Exception as e:
                print(f"❌ 스크린샷 촬영 중 오류: {str(e)}")
                try:
                    await context.close()
                    await browser.close()
                except:
                    pass
                raise

    async def check_login_status(self, page, url):
        """웹사이트별 로그인 상태 확인"""
        try:
            if "naver.com" in url:
                try:
                    login_button = await page.query_selector('a[href*="login"]')
                    if login_button:
                        print("🔓 네이버: 로그인되지 않은 상태")
                    else:
                        user_info = await page.query_selector(
                            '.gnb_name, [data-clk="gnb.myinfo"]'
                        )
                        if user_info:
                            print("🔐 네이버: 로그인된 상태 확인")
                        else:
                            print("🔍 네이버: 로그인 상태 불분명")
                except:
                    print("🔍 네이버: 로그인 상태 확인 실패")

            elif "google.com" in url:
                try:
                    profile_button = await page.query_selector("[data-ogsr-up], .gb_d")
                    if profile_button:
                        print("🔐 Google: 로그인된 상태 확인")
                    else:
                        print("🔓 Google: 로그인되지 않은 상태")
                except:
                    print("🔍 Google: 로그인 상태 확인 실패")

        except Exception as e:
            print(f"🔍 로그인 상태 확인 중 오류: {e}")

    async def take_screenshot(
        self, profile_name, url="https://www.naver.com", output_dir="./screenshots"
    ):
        """메인 스크린샷 메서드"""
        self.kill_existing_chrome_processes()

        try:
            return await self.take_screenshot_with_launch(profile_name, url, output_dir)
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
        print("🖥️  Chrome 프로필 스크린샷 도구 (launch 방식)")
        print("=" * 55)

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

        print(f"\n🎯 작업 시작: Chrome 프로필 '{profile_name}' 사용")
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
        print(f"   1. Chrome을 완전히 종료한 후 재시도")
        print(f"   2. 프로필이 손상되었을 수 있음 - 다른 프로필로 테스트")
        print(f"   3. Chrome을 수동으로 해당 프로필로 한 번 실행해보기")
        print(f"   4. 네트워크 연결 상태 확인")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
