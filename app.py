import streamlit as st
import requests
import time
import json
import base64
from playwright.sync_api import sync_playwright
import subprocess
import os

# Ensure Playwright browsers are installed on startup
def ensure_playwright_browsers():
    playwright_dir = os.path.expanduser("~/.cache/ms-playwright")
    chromium_dir = os.path.join(playwright_dir, "chromium-1105")  # Adjust version if needed
    if not os.path.exists(chromium_dir):
        try:
            st.info("Installing Playwright Chromium browser... This may take a moment on first run.")
            subprocess.run(["playwright", "install", "chromium"], check=True)
            st.success("Playwright Chromium installed successfully!")
        except subprocess.CalledProcessError as e:
            st.error(f"Failed to install Playwright browsers: {e}. UI tests may not work.")

# Run this on app startup
ensure_playwright_browsers()

# Initialize session state
if "saved_tests" not in st.session_state:
    st.session_state.saved_tests = []
if "api_response" not in st.session_state:
    st.session_state.api_response = None

# Cached Playwright test function with all enhancements
@st.cache_data
def run_playwright_tests(url, tests_to_run, search_text="", custom_selector=""):
    results = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            start_time = time.time()
            response = page.goto(url, wait_until="domcontentloaded", timeout=30000)  # 30s timeout
            
            if "title" in tests_to_run:
                results["title"] = {"status": "success", "value": page.title() or "No title found"}
            if "status" in tests_to_run:
                if response:
                    status_code = response.status
                    if status_code == 200:
                        results["status"] = {"status": "success", "value": "Site is live (200 OK)"}
                    elif status_code == 404:
                        results["status"] = {"status": "error", "value": "Site not found (404)"}
                    elif status_code == 503:
                        results["status"] = {"status": "error", "value": "Service unavailable (503)"}
                    else:
                        results["status"] = {"status": "warning", "value": f"Site returned status {status_code}"}
                else:
                    results["status"] = {"status": "error", "value": "Failed to load site"}
            if "header" in tests_to_run:
                header = page.query_selector("header")
                results["header"] = {"status": "success" if header else "error", 
                                    "value": "Header found" if header else "No header found"}
            if "footer" in tests_to_run:
                footer = page.query_selector("footer")
                results["footer"] = {"status": "success" if footer else "error", 
                                    "value": "Footer found" if footer else "No footer found"}
            if "links" in tests_to_run:
                links = page.query_selector_all("a")
                results["links"] = {"status": "success" if links else "warning", 
                                   "value": f"{len(links)} link(s) found" if links else "No links found"}
            if "images" in tests_to_run:
                images = page.query_selector_all("img")
                results["images"] = {"status": "success" if images else "warning", 
                                    "value": f"{len(images)} image(s) found" if images else "No images found"}
            if "text" in tests_to_run and search_text:
                is_present = page.query_selector(f"//*[contains(text(), '{search_text}')]") is not None
                results["text"] = {"status": "success" if is_present else "error", 
                                  "value": f"Text '{search_text}' found" if is_present else f"Text '{search_text}' not found"}
            if "load_time" in tests_to_run:
                load_time = time.time() - start_time
                results["load_time"] = {"status": "success" if load_time < 5 else "warning", 
                                       "value": f"Loaded in {load_time:.2f} seconds" + 
                                                (" (slow)" if load_time >= 5 else "")}
            if "forms" in tests_to_run:
                forms = page.query_selector_all("form")
                results["forms"] = {"status": "success" if forms else "warning", 
                                   "value": f"{len(forms)} form(s) found" if forms else "No forms found"}
            if "custom" in tests_to_run and custom_selector:
                element = page.query_selector(custom_selector)
                results["custom"] = {"status": "success" if element else "error", 
                                    "value": f"Element '{custom_selector}' found" if element else f"Element '{custom_selector}' not found"}
            if "screenshot" in tests_to_run:
                screenshot = page.screenshot()
                results["screenshot"] = {"status": "success", "value": base64.b64encode(screenshot).decode()}
            if "accessibility" in tests_to_run:
                images = page.query_selector_all("img")
                missing_alt = sum(1 for img in images if not img.get_attribute("alt"))
                results["accessibility"] = {"status": "success" if missing_alt == 0 else "warning", 
                                           "value": f"{missing_alt} image(s) missing alt text" if missing_alt > 0 else "All images have alt text"}
            
            browser.close()
    except Exception as e:
        error_msg = str(e)
        if "Timeout" in error_msg:
            return {"error": "The site took too long to load. Check the URL or try again later."}
        elif "net::ERR" in error_msg:
            return {"error": "Couldn’t connect to the site. Make sure the URL is correct and the site is online."}
        else:
            return {"error": f"Something went wrong: {error_msg}. Try a different URL or reset the test."}
    return results

# Streamlit app layout
st.set_page_config(page_title="API Testing Utility", layout="wide")

# Sidebar for navigation
st.sidebar.title("API Testing Utility")
st.sidebar.write("Test APIs and UI seamlessly.")
menu = st.sidebar.radio("Navigate", ["Test API & UI", "Saved Tests"], help="Switch between testing and viewing saved tests.")

if menu == "Test API & UI":
    st.title("API & UI Tester")
    st.write("Test APIs and webpages with ease.")

    # Two-column layout
    col1, col2 = st.columns([2, 3])

    with col1:
        # API Form
        with st.form("api_form"):
            endpoint = st.text_input("API Endpoint", placeholder="e.g., https://jsonplaceholder.typicode.com/posts/1", 
                                    help="Enter an API URL to test.")
            method = st.selectbox("Request Method", ["GET", "POST", "PUT", "DELETE"], help="Choose the HTTP method.")
            headers = st.text_area("Headers (JSON)", '{"Content-Type": "application/json"}', 
                                  help="Enter headers as JSON.")
            body = st.text_area("Request Body (JSON)", "{}" if method in ["POST", "PUT"] else "", 
                               help="Enter body as JSON (ignored for GET/DELETE).")
            submit = st.form_submit_button("Send API Request", help="Send the API request.")

        # API Response Handling and Saving
        if submit and endpoint:
            with st.spinner("Sending API request..."):
                try:
                    headers_dict = json.loads(headers)
                    start_time = time.time()
                    response = requests.request(method, endpoint, headers=headers_dict, 
                                              data=body if method in ["POST", "PUT"] else None, timeout=10)
                    response_time = time.time() - start_time
                    st.session_state.api_response = {
                        "status_code": response.status_code,
                        "response_time": response_time,
                        "data": response.json() if response.text else "No JSON response"
                    }
                except requests.exceptions.Timeout:
                    st.session_state.api_response = {"error": "The API took too long to respond. Check the URL or try again later."}
                except requests.exceptions.ConnectionError:
                    st.session_state.api_response = {"error": "Couldn’t connect to the API. Make sure the URL is correct and the server is online."}
                except json.JSONDecodeError:
                    st.session_state.api_response = {"error": "The headers or response isn’t valid JSON. Check your input and try again."}
                except Exception as e:
                    st.session_state.api_response = {"error": f"Something went wrong: {str(e)}. Reset the test or try a different URL."}

        if st.session_state.api_response and "error" not in st.session_state.api_response:
            if st.button("Save This API Test", help="Save this successful API test for this session."):
                test_config = {
                    "type": "api",
                    "name": f"Test {len(st.session_state.saved_tests) + 1} API",
                    "endpoint": endpoint,
                    "method": method,
                    "headers": headers,
                    "body": body
                }
                st.session_state.saved_tests.append(test_config)
                st.success(f"Saved as {test_config['name']} for this session!")

        # Playwright UI Test Form
        st.subheader("UI Test Options")
        ui_url = st.text_input("Webpage URL", value="https://example.com", help="Enter a webpage URL to test.")
        ui_tests = st.multiselect("Select UI Tests", 
                                 ["title", "status", "header", "footer", "links", "images", "text", "load_time", "forms", "custom", "screenshot", "accessibility"], 
                                 default=["title"], help="Choose what to check on the webpage.")
        search_text = st.text_input("Search Text (for 'text' test)", "", 
                                   help="Enter text to search for if 'text' is selected.") if "text" in ui_tests else ""
        custom_selector = st.text_input("Custom CSS Selector (for 'custom' test)", "", 
                                       help="Enter a selector like '#id' or '.class' if 'custom' is selected.") if "custom" in ui_tests else ""
        if st.button("Run UI Test", help="Test the webpage with selected options."):
            st.session_state.ui_results = run_playwright_tests(ui_url, ui_tests, search_text, custom_selector)
            test_config = {
                "type": "ui",
                "name": f"Test {len(st.session_state.saved_tests) + 1} UI",
                "url": ui_url,
                "tests": ui_tests,
                "search_text": search_text,
                "custom_selector": custom_selector
            }
            if "ui_results" in st.session_state and "error" not in st.session_state.ui_results:
                st.session_state.saved_tests.append(test_config)
                st.success(f"Saved as {test_config['name']} for this session!")

        if st.button("Reset Tests", help="Clear all saved tests from this session."):
            st.session_state.saved_tests = []
            if "ui_results" in st.session_state:
                del st.session_state.ui_results
            if "api_response" in st.session_state:
                del st.session_state.api_response
            st.success("All tests reset!")

    with col2:
        # API Response Display
        st.subheader("API Response")
        if "api_response" in st.session_state and st.session_state.api_response is not None:
            if "error" in st.session_state.api_response:
                st.error(st.session_state.api_response["error"])
                st.info("What to do: Check the URL, ensure it’s valid, or reset the test.")
            else:
                st.write(f"**Status Code**: {st.session_state.api_response['status_code']}")
                st.write(f"**Response Time**: {st.session_state.api_response['response_time']:.2f} seconds")
                st.json(st.session_state.api_response['data'])
        else:
            st.info("No API response available. Please make a request.")

        # UI Test Results
        if "ui_results" in st.session_state:
            st.subheader("UI Test Results")
            results = st.session_state.ui_results
            if "error" in results:
                st.error(results["error"])
                st.info("What to do: Check the URL, ensure it’s a valid webpage, or reset the test.")
            else:
                for test, result in results.items():
                    if test == "screenshot":
                        if result["status"] == "success":
                            st.image(base64.b64decode(result["value"]), caption="Page Screenshot", use_container_width=True)
                    else:
                        if result["status"] == "success":
                            st.success(f"{test.capitalize()}: {result['value']}")
                        elif result["status"] == "error":
                            st.error(f"{test.capitalize()}: {result['value']}")
                            st.info(f"What to do: The {test} check failed. Verify the webpage has a {test} or try a different URL.")
                        elif result["status"] == "warning":
                            st.warning(f"{test.capitalize()}: {result['value']}")

elif menu == "Saved Tests":
    st.title("Saved Tests")
    st.write("View tests saved in this session.")
    if not st.session_state.saved_tests:
        st.info("No tests saved yet. Run and save some tests!")
    else:
        for i, test in enumerate(st.session_state.saved_tests):
            with st.expander(f"{test['name']}"):
                if test["type"] == "api":
                    st.write(f"**Type**: API")
                    st.write(f"**Method**: {test['method']}")
                    st.write(f"**Endpoint**: {test['endpoint']}")
                    st.json(json.loads(test['headers']), expanded=False)
                    if test['body']:
                        st.json(json.loads(test['body']), expanded=False)
                    if st.button(f"Run {test['name']}", help="Re-run this API test."):
                        with st.spinner("Running API test..."):
                            try:
                                headers_dict = json.loads(test['headers'])
                                response = requests.request(test['method'], test['endpoint'], headers=headers_dict, 
                                                          data=test['body'] if test['method'] in ["POST", "PUT"] else None)
                                st.write(f"**Status Code**: {response.status_code}")
                                st.json(response.json() if response.text else "No JSON response")
                            except Exception as e:
                                st.error(f"Failed to run test: {str(e)}. Check the URL or reset tests.")
                elif test["type"] == "ui":
                    st.write(f"**Type**: UI")
                    st.write(f"**URL**: {test['url']}")
                    st.write(f"**Tests**: {', '.join(test['tests'])}")
                    if test.get("search_text"):
                        st.write(f"**Search Text**: {test['search_text']}")
                    if test.get("custom_selector"):
                        st.write(f"**Custom Selector**: {test['custom_selector']}")
                    if st.button(f"Run {test['name']}", help="Re-run this UI test."):
                        with st.spinner("Running UI test..."):
                            results = run_playwright_tests(test["url"], test["tests"], 
                                                          test.get("search_text", ""), test.get("custom_selector", ""))
                            if "error" in results:
                                st.error(results["error"])
                            else:
                                for t, r in results.items():
                                    if t == "screenshot":
                                        st.image(base64.b64decode(r["value"]), caption="Page Screenshot", use_container_width=True)
                                    else:
                                        st.success(f"{t.capitalize()}: {r['value']}" if r["status"] == "success" else f"{t.capitalize()}: {r['value']}")

# Footer
st.sidebar.markdown("---")
st.sidebar.write("Built with ❤️ by [itswale](https://www.linkedin.com/in/itswale/)")