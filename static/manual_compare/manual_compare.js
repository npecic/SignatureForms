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
        }
    } catch (error) {
        console.error('Error fetching images:', error);
    }
}


function updateImages(index) {
    if (images.length > 0) {
        document.getElementById('original-image').src = images[index].original;
        document.getElementById('bounding-box-image').src = images[index].bounding_box;
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

// Initialize
fetchImages();
