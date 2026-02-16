$(document).ready(function() {

	// Smooth Scroll to internal links

	$(".scroll").click(function(event){		
			event.preventDefault();
			
			$scroll = $(this.hash).offset().top;
			$scroll = $scroll - 90;
			$('html,body').animate({scrollTop:$scroll}, 500);
		});

	// Handle hover event for the project images

	$(".project-img-wrap").mouseenter(function(){
			$(this).children('.project-hover').fadeIn(200);
		}).mouseleave(function(){
		  $(this).children('.project-hover').fadeOut(200);
		});	

});