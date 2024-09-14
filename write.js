function loadFile(input) {
    let file = input.files[0]; // 선택파일 가져오기

    let newImage = document.createElement("img"); //새 이미지 태그 생성

    //이미지 source 가져오기
    newImage.src = URL.createObjectURL(file);
    newImage.style.width = "100%"; //div에 꽉차게 넣으려고
    newImage.style.height = "100%";
    newImage.style.objectFit = "cover"; // div에 넘치지 않고 들어가게

    //이미지를 image-show div에 추가
    let container = document.getElementById('image-show');
    container.appendChild(newImage);
}

document.querySelector('.upload-btn').addEventListener('click', function() {
    alert('글이 업로드되었습니다.');
        // function hat2Img() {
    //     document.getElementById("img").src = "./images/rose.jpg";
});







// -------------------------------------------- //







// 모달 열기
// 모달 열기
// 모달 열기
function openModal(modalId) {
    document.getElementById(modalId).style.display = "block";
}

// 모달 닫기
function closeModal(modalId) {
    document.getElementById(modalId).style.display = "none";
}

// 세분화된 지역 모달 열기
function openSubRegionModal(modalId) {
    closeModal('region-modal'); // 기존 지역 모달 닫기
    openModal(modalId); // 세분화된 지역 모달 열기
}

// 모달 외부 클릭 시 닫기
window.onclick = function(event) {
    const modals = document.getElementsByClassName('modal');
    for (let i = 0; i < modals.length; i++) {
        if (event.target == modals[i]) {
            modals[i].style.display = "none";
        }
    }
}

// 텍스트 대체 함수
function selectOption(buttonId, optionText) {
    document.getElementById(buttonId).innerText = optionText;
    closeModal(buttonId.replace('-button', '-modal'));
}
