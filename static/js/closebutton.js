document.getElementById('menu-button').addEventListener('click', function () {
    document.getElementById('mobile-menu').classList.remove('hidden');
});

document.getElementById('close-button').addEventListener('click', function () {
    document.getElementById('mobile-menu').classList.add('hidden');
});