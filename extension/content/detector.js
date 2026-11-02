window.addEventListener("message", (event) => {
  if (event.data?.type === "reviewflow-ping") {
    window.postMessage({ type: "reviewflow-pong", version: "1.1.0" }, "*");
  }
  if (event.data?.type === "reviewflow-set-token") {
    chrome.runtime.sendMessage({
      type: "SET_TOKEN",
      token: event.data.token,
      apiUrl: event.data.apiUrl,
      platformConnectionId: event.data.platformConnectionId,
    });
  }
});
