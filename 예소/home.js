document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('.tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
        });
    });
});
function clearSearch() {
    document.querySelector('.search-bar').value = '';  // 검색창을 선택하고 그 값을 비웁니다.
}

