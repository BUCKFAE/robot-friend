(function () {
  var KEY = "finch-grid-layout-v3";

  function init() {
    if (!window.GridStack) {
      return setTimeout(init, 50);
    }

    var el = document.querySelector(".grid-stack");
    if (!el || !el.querySelector(".grid-stack-item")) {
      return setTimeout(init, 50);
    }

    if (el.__gridstack) {
      return;
    }

    var grid = GridStack.init({
      float: true,
      column: 12,
      cellHeight: 88,
      margin: 6,
      resizable: { handles: "se" },
    }, el);
    el.__gridstack = grid;

    try {
      var saved = localStorage.getItem(KEY);
      if (saved) {
        grid.load(JSON.parse(saved), false);
      }
    } catch (e) {}

    grid.on("change", function () {
      try {
        localStorage.setItem(KEY, JSON.stringify(grid.save(false)));
      } catch (e) {}
    });
  }

  init();
})();
