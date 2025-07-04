let currentPage = 0;
document.getElementById('prevPage')?.addEventListener('click', () => {
  if (currentPage > 0) {
    currentPage--;
    updatePage();
  }
});
document.getElementById('nextPage')?.addEventListener('click', () => {
  currentPage++;
  updatePage();
});
function updatePage() {
  let iframe = document.getElementById('pdfViewer');
  iframe.src = iframe.src.replace(/page=\d+/, `page=${currentPage}`);
}
function updateRoute() {
  const date = document.getElementById('datePicker').value;
  const district = document.getElementById('districtPicker').value;
  window.location.href = `/?date=${date}&district=${district}`;
}

document.getElementById('datePicker')?.addEventListener('change', updateRoute);
document.getElementById('districtPicker')?.addEventListener('change', updateRoute);


function togglePassword(id, el) {
  const input = document.getElementById(id);
  if (input.type === "password") {
    input.type = "text";
    el.textContent = "👁";
  } else {
    input.type = "password";
    el.textContent = "👁";
  }
}
