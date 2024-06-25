document.addEventListener('DOMContentLoaded', () => {
    let currentIndex = 0;
    let images = [];

    async function fetchImages() {
        try {
            const response = await fetch('/api/get_compare_images');
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            images = data.images;
            if (images.length > 0) {
                updateImages(0);
            } else {
                document.getElementById('original-image').src = '';
                document.getElementById('bounding-box-image').src = '';
                document.getElementById('message').textContent = '';
            }
        } catch (error) {
            console.error('Error fetching images:', error);
        }
    }

    function updateImages(index) {
        if (images.length > 0) {
            document.getElementById('original-image').src = images[index].original;
            document.getElementById('bounding-box-image').src = images[index].bounding_box;
            const filename = images[index].original.split('/').pop();
            document.getElementById('message').textContent = `Current pdf: ${filename}`;
        }
    }

    document.getElementById('prev-button').addEventListener('click', () => {
        currentIndex = Math.max(currentIndex - 1, 0);
        updateImages(currentIndex);
    });

    document.getElementById('next-button').addEventListener('click', () => {
        currentIndex = Math.min(currentIndex + 1, images.length - 1);
        updateImages(currentIndex);
    });

    document.getElementById('fullscreen-button').addEventListener('click', () => {
        const fullscreenContainer = document.getElementById('fullscreen-container');
        fullscreenContainer.style.display = 'flex';
        fullscreenContainer.requestFullscreen().catch(err => {
            alert(`Error attempting to enable full-screen mode: ${err.message} (${err.name})`);
        });
        updateFullscreenImages();
    });

    document.addEventListener('fullscreenchange', () => {
        if (!document.fullscreenElement) {
            document.getElementById('fullscreen-container').style.display = 'none';
        }
    });

    function updateFullscreenImages() {
        document.getElementById('fullscreen-original-image').src = document.getElementById('original-image').src;
        document.getElementById('fullscreen-bounding-box-image').src = document.getElementById('bounding-box-image').src;
    }

    document.getElementById('fullscreen-prev-button').addEventListener('click', () => {
        currentIndex = Math.max(currentIndex - 1, 0);
        updateImages(currentIndex);
        updateFullscreenImages();
    });

    document.getElementById('fullscreen-next-button').addEventListener('click', () => {
        currentIndex = Math.min(currentIndex + 1, images.length - 1);
        updateImages(currentIndex);
        updateFullscreenImages();
    });

    let zoomLevel = 1;
    document.getElementById('fullscreen-original-image').addEventListener('wheel', (e) => {
        if (e.deltaY < 0) {
            zoomLevel += 0.1;
        } else {
            zoomLevel = Math.max(1, zoomLevel - 0.1);
        }
        document.getElementById('fullscreen-original-image').style.transform = `scale(${zoomLevel})`;
    });

    document.getElementById('fullscreen-bounding-box-image').addEventListener('wheel', (e) => {
        if (e.deltaY < 0) {
            zoomLevel += 0.1;
        } else {
            zoomLevel = Math.max(1, zoomLevel - 0.1);
        }
        document.getElementById('fullscreen-bounding-box-image').style.transform = `scale(${zoomLevel})`;
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'ArrowLeft') {
            document.getElementById('prev-button').click();
        } else if (event.key === 'ArrowRight') {
            document.getElementById('next-button').click();
        }
    });

    fetchImages();
});
