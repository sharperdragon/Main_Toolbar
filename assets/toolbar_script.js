let model = []; // hydrated from Python
let dragIndex = null;
let selectedIndex = null; // currently selected row

function rowHtml(r, i) {
  const esc = s => (s ?? "").toString().replace(/&/g,"&amp;").replace(/</g,"&lt;");
  return `
    <tr draggable="true" data-index="${i}">
      <td class="name-cell">
        <input value="${esc(r.name)}" placeholder="Name" onchange="onEdit(${i}, 'name', this.value)">
      </td>
      <td><input value="${esc(r.module)}" placeholder="Module (e.g., Main_Toolbar.modules...)" onchange="onEdit(${i}, 'module', this.value)"></td>
      <td><input value="${esc(r.function)}" placeholder="Function" onchange="onEdit(${i}, 'function', this.value)"></td>
      <td><input value="${esc(r.submenu)}" placeholder="Submenu" onchange="onEdit(${i}, 'submenu', this.value)"></td>
      <td><input value="${esc(r.icon)}" placeholder="icons/..." onchange="onEdit(${i}, 'icon', this.value)"></td>
      <td><input type="checkbox" ${r.enabled ? "checked": ""} onchange="onEdit(${i}, 'enabled', this.checked)"></td>
    </tr>
  `;
}

function selectRow(i) {
  selectedIndex = (typeof i === 'number' ? i : null);
  const tbody = document.getElementById('tbody');
  if (!tbody) return;
  tbody.querySelectorAll('tr').forEach((tr, idx) => {
    if (idx === selectedIndex) tr.classList.add('selected');
    else tr.classList.remove('selected');
  });
}

function render() {
  const tbody = document.getElementById("tbody");
  const prev = selectedIndex; // remember selection across rerenders
  tbody.innerHTML = model.map(rowHtml).join("");
  // wire dnd + selection
  tbody.querySelectorAll("tr").forEach(tr => {
    tr.addEventListener("dragstart", (e) => { dragIndex = +tr.dataset.index; });
    tr.addEventListener("dragover", (e) => e.preventDefault());
    tr.addEventListener("drop", (e) => {
      e.preventDefault();
      const to = +tr.dataset.index;
      if (dragIndex === null || to === dragIndex) return;
      const [moved] = model.splice(dragIndex, 1);
      model.splice(to, 0, moved);
      dragIndex = null;
      render();
      selectRow(to);
    });
    tr.addEventListener("click", () => selectRow(+tr.dataset.index));
  });
  // focusing an input selects the row
  tbody.querySelectorAll('input').forEach(inp => {
    inp.addEventListener('focus', (e) => {
      const tr = e.target.closest('tr');
      if (tr) selectRow(+tr.dataset.index);
    });
  });
  // restore previous selection if still valid
  if (prev != null && prev >= 0 && prev < model.length) selectRow(prev);
}

function onEdit(i, key, val) { model[i][key] = val; }
function onAdd() { model.push({name:"", module:"", function:"", submenu:"", icon:"", enabled:true}); render(); }
function onAddAfter(i) { model.splice(i+1, 0, {name:"", module:"", function:"", submenu:"", icon:"", enabled:true}); render(); }
function onDelete(i) { model.splice(i,1); render(); }
function onDivider(i) { model.splice(i+1, 0, {name:"———", module:"", function:"", submenu:"", icon:"", enabled:false, type:"separator"}); render(); }

function onAddGlobal() {
  onAdd();
  selectRow(model.length - 1);
}

function onAddDividerGlobal() {
  const divider = {name:"———", module:"", function:"", submenu:"", icon:"", enabled:false, type:"separator"};
  if (selectedIndex == null) {
    model.push(divider);
  } else {
    model.splice(selectedIndex + 1, 0, divider);
  }
  render();
}

function onDeleteGlobal() {
  if (!model.length) return;
  if (selectedIndex == null) {
    model.pop();
    render();
    return;
  }
  model.splice(selectedIndex, 1);
  selectedIndex = null;
  render();
}

function onSave() {
  // ensure Toolbar Settings row exists
  if (!model.some(x => (x.name || "").toLowerCase() === "toolbar settings")) {
    model.push({name:"Toolbar Settings", module:"Main_Toolbar.toolbar_editor", function:"edit_toolbar_json", submenu:"", icon:"icons/bent_menu-burger.svg", enabled:true});
  }
  const payload = JSON.stringify(model);
  pycmd("toolbar_editor:save:" + payload);
}

function hydrate(jsonStr) {
  try {
    model = JSON.parse(jsonStr);
  } catch(e) { model = []; }
  render();
}

function askRefresh() { pycmd("toolbar_editor:refresh"); }