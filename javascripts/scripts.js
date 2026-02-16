'use strict';

document.addEventListener('DOMContentLoaded', function() {
	
	// Smooth scroll to internal links (any anchor link starting with #)
	document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
		anchor.addEventListener('click', function(event) {
			const targetId = this.getAttribute('href');
			
			// Skip if href is just "#"
			if (targetId === '#') return;
			
			const target = document.querySelector(targetId);
			if (!target) return;
			
			event.preventDefault();
			
			const scrollPosition = target.offsetTop - 90;
			
			window.scrollTo({
				top: scrollPosition,
				behavior: 'smooth'
			});
		});
	});

	// Handle hover effect for project images
	document.querySelectorAll('.project-img-wrap').forEach(function(wrapper) {
		const hoverElement = wrapper.querySelector('.project-hover');
		if (!hoverElement) return;
		
		wrapper.addEventListener('mouseenter', function() {
			hoverElement.style.display = 'block';
			hoverElement.style.opacity = '0';
			
			// Trigger reflow to enable transition
			hoverElement.offsetHeight;
			
			hoverElement.style.transition = 'opacity 200ms ease';
			hoverElement.style.opacity = '1';
		});
		
		wrapper.addEventListener('mouseleave', function() {
			hoverElement.style.opacity = '0';
			
			setTimeout(function() {
				hoverElement.style.display = 'none';
			}, 200);
		});
	});

});