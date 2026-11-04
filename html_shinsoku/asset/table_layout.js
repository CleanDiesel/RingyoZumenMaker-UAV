/* Attribute tables never resize the map or cover its rendered content. */
(() => {
  const removeIds = element => {
    element.removeAttribute("id");
    element.querySelectorAll("[id]").forEach(child => child.removeAttribute("id"));
  };
  function paginateTables() {
    const factor = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--paper-factor")) || 1;
    const gap = 2 * 96 / 25.4 * factor;
    for (const sheet of [...document.querySelectorAll(".drawing-sheet:not(.attribute-continuation)")]) {
      const table = sheet.querySelector(".attribute-table");
      if (!table) continue;
      sheet.style.display = "block";
      const frame = sheet.querySelector(".map_container");
      const map = frame.querySelector(".map");
      const mapBox = map.getBoundingClientRect();
      const tableBox = table.getBoundingClientRect();
      const bottom = Number(map.dataset.contentBottom ?? 1);
      const occupied = mapBox.top + bottom * mapBox.height;
      if (occupied + gap <= tableBox.top && tableBox.height <= frame.clientHeight) {
        sheet.dataset.tablePlacement = "bottom";
        sheet.style.display = "";
        continue;
      }
      sheet.dataset.tablePlacement = "continuation";
      sheet.classList.remove("has-attribute-table");
      const rows = [...table.tBodies[0].rows];
      rows.forEach(row => row.remove());
      table.remove();
      let after = sheet, current, continuationFrame, pageNumber = 0;
      function newPage() {
        pageNumber++;
        const next = document.createElement("div");
        next.className = "drawing-sheet main_container attribute-continuation";
        next.dataset.drawing = sheet.dataset.drawing;
        next.dataset.title = sheet.dataset.title + "（属性表" + (pageNumber > 1 ? " " + pageNumber : "") + "）";
        next.append(sheet.querySelector("h1").cloneNode(true));
        const header = sheet.querySelector(".info_container").cloneNode(true);
        removeIds(header);
        next.append(header);
        const area = document.createElement("div");
        area.className = "sub_container";
        continuationFrame = document.createElement("div");
        continuationFrame.className = "attribute-frame";
        current = table.cloneNode(false);
        const columns = table.querySelector("colgroup");
        if (columns) current.append(columns.cloneNode(true));
        current.append(table.tHead.cloneNode(true), document.createElement("tbody"));
        continuationFrame.append(current);
        area.append(continuationFrame);
        next.append(area);
        after.after(next);
        next.style.display = "block";
        after = next;
      }
      const fits = () => current.getBoundingClientRect().height <= continuationFrame.clientHeight + .1;
      newPage();
      for (const row of rows) {
        current.tBodies[0].append(row);
        if (fits()) continue;
        row.remove();
        if (current.tBodies[0].rows.length) newPage();
        current.tBodies[0].append(row);
        if (fits()) continue;
        // A single very long feature must also fit, without truncating text.
        const remaining = [...row.cells].map(cell => Array.from(cell.textContent));
        row.remove();
        while (remaining.some(text => text.length)) {
          const part = row.cloneNode(true);
          [...part.cells].forEach(cell => cell.textContent = "");
          current.tBodies[0].append(part);
          for (let i = 0; i < part.cells.length; i++) {
            let low = 0, high = remaining[i].length;
            while (low < high) {
              const middle = Math.ceil((low + high) / 2);
              part.cells[i].textContent = remaining[i].slice(0, middle).join("");
              if (fits()) low = middle; else high = middle - 1;
            }
            part.cells[i].textContent = remaining[i].splice(0, low).join("");
          }
          if (![...part.cells].some(cell => cell.textContent)) throw new Error("属性表の見出しが用紙に収まりません。");
          if (remaining.some(text => text.length)) newPage();
        }
      }
      sheet.style.display = "";
    }
    document.querySelectorAll(".attribute-continuation").forEach(sheet => sheet.style.display = "");
  }
  window.RingyoLayout = {paginateTables};
})();
