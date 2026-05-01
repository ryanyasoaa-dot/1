// Carousel Functionality
let currentSlide = 0;
const slides = document.querySelectorAll('.hero-slide');
const dots = document.querySelectorAll('.carousel-dot');
const totalSlides = slides.length;

function showSlide(n) {
    slides.forEach(slide => slide.classList.remove('active'));
    dots.forEach(dot => dot.classList.remove('active'));
    slides[n].classList.add('active');
    dots[n].classList.add('active');
}

function nextSlide() {
    currentSlide = (currentSlide + 1) % totalSlides;
    showSlide(currentSlide);
}

function prevSlide() {
    currentSlide = (currentSlide - 1 + totalSlides) % totalSlides;
    showSlide(currentSlide);
}

setInterval(nextSlide, 6000);

document.getElementById('nextBtn').addEventListener('click', nextSlide);
document.getElementById('prevBtn').addEventListener('click', prevSlide);

dots.forEach((dot, index) => {
    dot.addEventListener('click', () => {
        currentSlide = index;
        showSlide(currentSlide);
    });
});

// Countdown Timer
function updateCountdown() {
    const hoursEl = document.getElementById('hours');
    const minutesEl = document.getElementById('minutes');
    const secondsEl = document.getElementById('seconds');

    let hours = parseInt(hoursEl.textContent);
    let minutes = parseInt(minutesEl.textContent);
    let seconds = parseInt(secondsEl.textContent);

    if (seconds > 0) {
        seconds--;
    } else if (minutes > 0) {
        seconds = 59;
        minutes--;
    } else if (hours > 0) {
        minutes = 59;
        seconds = 59;
        hours--;
    } else {
        hours = 6;
        minutes = 0;
        seconds = 0;
    }

    hoursEl.textContent = String(hours).padStart(2, '0');
    minutesEl.textContent = String(minutes).padStart(2, '0');
    secondsEl.textContent = String(seconds).padStart(2, '0');
}

setInterval(updateCountdown, 1000);

// Hamburger Menu
const hamburger = document.getElementById('hamburger');
const navLinks = document.getElementById('navLinks');

hamburger.addEventListener('click', () => {
    hamburger.classList.toggle('active');
    navLinks.style.display = navLinks.style.display === 'flex' ? 'none' : 'flex';
});

navLinks.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
        hamburger.classList.remove('active');
        navLinks.style.display = 'none';
    });
});

// Quick Add to Cart
document.querySelectorAll('.quick-add-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const productCard = e.target.closest('.product-card');
        const productName = productCard.querySelector('.product-name').textContent;

        const originalText = btn.textContent;
        btn.textContent = '✓ Added!';
        btn.style.backgroundColor = 'rgba(76, 175, 80, 0.8)';

        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.backgroundColor = '';
        }, 2000);

        console.log(`Added ${productName} to cart`);
    });
});

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#' && document.querySelector(href)) {
            e.preventDefault();
            document.querySelector(href).scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});
