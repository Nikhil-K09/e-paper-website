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
document.getElementById('datePicker')?.addEventListener('change', e => {
  let district = document.getElementById('districtPicker').value;
  window.location.href = `/?date=${e.target.value}&district=${district}`;
});
document.getElementById('districtPicker')?.addEventListener('change', e => {
  let date = document.getElementById('datePicker').value;
  window.location.href = `/?date=${date}&district=${e.target.value}`;
});
