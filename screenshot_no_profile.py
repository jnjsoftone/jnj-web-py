#!/usr/bin/env python3
import os
import sys
import asyncio
import subprocess
import time
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
        """기존 Chrome 프로세스 종료 (동기 함수)"""
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
                            subprocess.run(["kill", pid], check=True)
                            print(f"   ✅ 프로세스 {pid} 종료됨")
                        except subprocess.CalledProcessError:
                            print(f"   ⚠️  프로세스 {pid} 종료 실패")

                    # 프로세스 종료 대기
                    print("   ⏳ Chrome 종료 대기 중...")
                    time.sleep(3)
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

    async def take_screenshot_simple(
        self, profile_name, url="https://www.naver.com", output_dir="./screenshots"
    ):
        """간단한 스크린샷 방법"""
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_profile_name = profile_name.replace(" ", "_").replace("/", "_")
        filename = f"screenshot_{safe_profile_name}_{timestamp}.png"
        output_path = os.path.join(output_dir, filename)

        print(f"\n🚀 Chrome 스크린샷 촬영")
        print(f"   프로필: {profile_name}")
        print(f"   URL: {url}")
        print(f"   출력 파일: {output_path}")

        async with async_playwright() as p:
            try:
                print(f"🌐 Chrome 브라우저를 시작합니다...")

                browser = await p.chromium.launch(
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
                        "--disable-blink-features=AutomationControlled",
                        "--exclude-switches=enable-automation",
                        "--disable-extensions-except",
                        "--disable-plugins-discovery",
                        "--start-maximized",
                    ],
                )

                # 새 컨텍스트 생성
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )

                page = await context.new_page()

                print(f"📄 페이지로 이동 중: {url}")

                # 네트워크 유휴 상태까지 기다리기
                try:
                    response = await page.goto(
                        url, wait_until="networkidle", timeout=30000
                    )
                    print(f"📡 응답 상태: {response.status if response else 'None'}")
                except Exception as e:
                    print(f"⚠️  networkidle 대기 실패, domcontentloaded로 재시도: {e}")
                    response = await page.goto(
                        url, wait_until="domcontentloaded", timeout=30000
                    )
                    print(f"📡 응답 상태: {response.status if response else 'None'}")

                # 추가 대기
                print(f"⏳ 페이지 렌더링 완료 대기 중...")
                await page.wait_for_timeout(5000)

                # 현재 URL과 제목 확인
                current_url = page.url
                current_title = await page.title()
                print(f"🔍 현재 URL: {current_url}")
                print(f"📋 페이지 제목: {current_title}")

                # about:blank 체크
                if current_url == "about:blank" or not current_title:
                    print(
                        "⚠️  페이지가 제대로 로드되지 않았습니다. JavaScript로 재시도..."
                    )

                    # JavaScript로 강제 이동
                    await page.evaluate(
                        f"""
                        window.location.replace('{url}');
                    """
                    )

                    # 다시 대기
                    await page.wait_for_timeout(8000)

                    # 상태 재확인
                    current_url = page.url
                    current_title = await page.title()
                    print(f"🔍 재시도 후 URL: {current_url}")
                    print(f"📋 재시도 후 제목: {current_title}")

                print(f"📸 스크린샷 촬영 중...")

                # 전체 페이지 스크린샷
                await page.screenshot(path=output_path, full_page=True, type="png")

                print(f"✅ 스크린샷이 성공적으로 저장되었습니다!")
                print(f"   📁 파일: {output_path}")

                # 파일 크기 확인
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"   📊 파일 크기: {file_size / 1024:.1f} KB")

                print(f"\n⏰ 5초 후 브라우저를 닫습니다...")
                await page.wait_for_timeout(5000)

                await context.close()
                await browser.close()

                return output_path

            except Exception as e:
                print(f"❌ 스크린샷 촬영 실패: {str(e)}")
                # 브라우저가 열려있다면 정리
                try:
                    await context.close()
                    await browser.close()
                except:
                    pass
                raise

    async def take_screenshot_with_profile(
        self, profile_name, url="https://www.naver.com", output_dir="./screenshots"
    ):
        """프로필을 사용한 스크린샷 방법"""
        profile_path = self.validate_profile(profile_name)
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_profile_name = profile_name.replace(" ", "_").replace("/", "_")
        filename = f"screenshot_{safe_profile_name}_{timestamp}_with_profile.png"
        output_path = os.path.join(output_dir, filename)

        print(f"\n🚀 프로필 사용 스크린샷 촬영")
        print(f"   프로필: {profile_name}")
        print(f"   프로필 경로: {profile_path}")
        print(f"   URL: {url}")
        print(f"   출력 파일: {output_path}")

        # 임시 사용자 데이터 디렉토리 생성
        temp_user_data = f"/tmp/chrome-playwright-{timestamp}"
        os.makedirs(temp_user_data, exist_ok=True)

        try:
            async with async_playwright() as p:
                print(f"🌐 Chrome 브라우저를 프로필과 함께 시작합니다...")

                context = await p.chromium.launch_persistent_context(
                    user_data_dir=temp_user_data,
                    executable_path=self.chrome_executable,
                    headless=False,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--start-maximized",
                    ],
                    viewport={"width": 1920, "height": 1080},
                )

                page = await context.new_page()

                print(f"📄 페이지로 이동 중: {url}")

                # 페이지 이동
                response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=30000
                )
                print(f"📡 응답 상태: {response.status if response else 'None'}")

                # 페이지 로딩 대기
                print(f"⏳ 페이지 렌더링 완료 대기 중...")
                await page.wait_for_timeout(5000)

                # 현재 상태 확인
                current_url = page.url
                current_title = await page.title()
                print(f"🔍 현재 URL: {current_url}")
                print(f"📋 페이지 제목: {current_title}")

                print(f"📸 스크린샷 촬영 중...")

                await page.screenshot(path=output_path, full_page=True, type="png")

                print(f"✅ 스크린샷이 성공적으로 저장되었습니다!")
                print(f"   📁 파일: {output_path}")

                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    print(f"   📊 파일 크기: {file_size / 1024:.1f} KB")

                print(f"\n⏰ 5초 후 브라우저를 닫습니다...")
                await page.wait_for_timeout(5000)

                await context.close()

                return output_path

        finally:
            # 임시 디렉토리 정리
            import shutil

            try:
                shutil.rmtree(temp_user_data, ignore_errors=True)
            except:
                pass

    async def take_screenshot(
        self, profile_name, url="https://www.naver.com", output_dir="./screenshots"
    ):
        """메인 스크린샷 메서드"""

        # 기존 Chrome 프로세스 확인 (동기 함수로 호출)
        self.kill_existing_chrome_processes()

        methods = [
            ("간단한 방법", self.take_screenshot_simple),
            ("프로필 사용 방법", self.take_screenshot_with_profile),
        ]

        for method_name, method_func in methods:
            try:
                print(f"\n🎯 {method_name} 시도 중...")
                result = await method_func(profile_name, url, output_dir)
                print(f"✅ {method_name} 성공!")
                return result
            except Exception as e:
                print(f"❌ {method_name} 실패: {str(e)}")
                if method_func == methods[-1][1]:  # 마지막 방법이면
                    raise
                else:
                    print(f"🔄 다음 방법을 시도합니다...\n")
                    await asyncio.sleep(2)

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
                    size = sum(
                        f.stat().st_size for f in profile_path.rglob("*") if f.is_file()
                    )
                    size_mb = size / (1024 * 1024)
                    print(f"      {i}. {profile} ({size_mb:.1f}MB)")
                except:
                    print(f"      {i}. {profile}")

            if len(available_profiles) > display_count:
                print(f"      ... 및 {len(available_profiles) - display_count}개 더")
        else:
            print(f"   ⚠️  사용 가능한 프로필이 없습니다.")


async def main():
    """메인 함수"""
    try:
        print("🖥️  Chrome 프로필 스크린샷 도구")
        print("=" * 50)

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

        # 스크린샷 촬영
        output_path = await screenshot_tool.take_screenshot(profile_name, url)

        print(f"\n🎉 작업 완료!")
        print(f"   📸 스크린샷: {output_path}")
        print(f"   🔍 Finder에서 열기: open {os.path.dirname(output_path)}")

    except KeyboardInterrupt:
        print("\n\n⏹️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 최종 오류: {str(e)}")
        print(f"\n🔧 해결 방법:")
        print(f"   1. Chrome을 완전히 종료한 후 재시도")
        print(f"   2. 네트워크 연결 확인")
        print(f"   3. 다른 URL로 테스트 (예: https://www.google.com)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
