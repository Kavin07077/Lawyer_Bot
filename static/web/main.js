/**
 * Returns the current datetime for the message creation.
 */
function getCurrentTimestamp() {
	return new Date();
}

/**
 * Renders a message on the chat screen based on the given arguments.
 * This is called from the `showUserMessage` and `showBotMessage`.
 en-IN
 */
function renderMessageToScreen(args) {
	// local variables
	let displayDate = (args.time || getCurrentTimestamp()).toLocaleString('en', {
		month: 'short',
		day: 'numeric',
		hour: 'numeric',
		minute: 'numeric',
	});
	let messagesContainer = $('.messages');

	// init element
	let message = $(`
	<li class="message ${args.message_side}">
		<div class="avatar"></div>
		<div class="text_wrapper">
			<div class="text">${args.text}</div>
			<div class="timestamp">${displayDate}</div>
		</div>
	</li>
	`);

	// add to parent
	messagesContainer.append(message);

	// animations
	setTimeout(function () { 
		message.addClass('appeared');
	}, 0);
	messagesContainer.animate({ scrollTop: messagesContainer.prop('scrollHeight') }, 300);
}

/**
 * Displays the user message on the chat screen. This is the right side message.
 */
function showUserMessage(message, datetime) {
	renderMessageToScreen({
		
		text: message,
		time: datetime,
		message_side: 'right',
	});
}

/**
 * Displays the chatbot message on the chat screen. This is the left side message.
 */
function showBotMessage(message, datetime) {
	renderMessageToScreen({
		
		text: message,
		time: datetime,
		message_side: 'left',
		
	});
}

/**
 * Get input from user and show it on screen on button click.
 */
//$('#send_button').on('click', function (e) {
$(function() {
    $('button').click(function() {
							   
							   
	var result="";
	// get and show message and reset input
	//showUserMessage($('#msg_input').val());
	//var minput = $('#msg_input').val('');
	
	$.ajax({
            url: '/bot',
            data: $('form').serialize(),
            type: 'POST',
			
			
            success: function(response) {
				showUserMessage($('input:text[name=msg_input]').val());
				document.form1.msg_input.value="";
            		//alert(response);
				
					showBotMessage(response);
        		
                //console.log(response);
            },
            error: function(error) {
                console.log(error);
            }
        });
	/////
	//result="hello";
	// show bot message
	/*setTimeout(function () {
		//showBotMessage(randomstring());
		showBotMessage(result);
	}, 300);*/
	
							   });
});


/**
 * Returns a random string. Just to specify bot message to the user.
 */
function randomstring(length = 20) {
	let output = '';

	// magic function
	var randomchar = function () {
		var n = Math.floor(Math.random() * 62);
		if (n < 10) return n;
		if (n < 36) return String.fromCharCode(n + 55);
		return String.fromCharCode(n + 61);
	};

	while (output.length < length) output += randomchar();
	return output;
}

/**
 * Set initial bot message to the screen for the user.
 */
$(window).on('load', function () {
	var m=' <img src="../static/img/e1.jpg" width="40" height="40">';
	showBotMessage('Hi! Welcome to LawyerBot! Type in a message ');
});
