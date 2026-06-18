function websocketUrl(path) {
  const scheme = window.location.protocol === "https:" ? "wss:" : "ws:";
  return scheme + "//" + window.location.host + path;
}

function connectVideoImage(image) {
  const path = image.getAttribute("data-vws");
  if (!path || image.dataset.wsConnected === "true") {
    return;
  }

  image.dataset.wsConnected = "true";
  let lastUrl = "";

  function connect() {
    const socket = new WebSocket(websocketUrl(path));
    socket.binaryType = "blob";

    socket.onmessage = function (event) {
      const nextUrl = URL.createObjectURL(event.data);
      const next = new Image();
      next.decoding = "async";
      next.onload = function () {
        image.src = nextUrl;
        if (lastUrl) {
          URL.revokeObjectURL(lastUrl);
        }
        lastUrl = nextUrl;
      };
      next.onerror = function () {
        URL.revokeObjectURL(nextUrl);
      };
      next.src = nextUrl;
    };

    socket.onclose = function () {
      image.dataset.wsConnected = "false";
      if (!document.hidden) {
        window.setTimeout(connect, 1000);
      }
    };
  }

  connect();
}

function connectVideoImages() {
  document.querySelectorAll("img[data-vws]").forEach(connectVideoImage);
}

document.addEventListener("visibilitychange", function () {
  if (!document.hidden) {
    connectVideoImages();
  }
});

window.setInterval(connectVideoImages, 500);
