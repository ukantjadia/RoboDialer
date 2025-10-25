from flask_mail import Mail, Message

mail = Mail()

def init_mail(app):
    mail.init_app(app)


def send_email(subject, recipients, html_body):
    msg = Message(subject, recipients=recipients, html=html_body)
    mail.send(msg)

def send_outreach_confirmation_email(recipient_email, username):
    subject = "Action Required: Your Pro Call Outreach Program Details!"
    html_body = f'''
        <p>Dear {username},</p>
        <p>Thank you for subscribing to the <strong>Pro Call Outreach</strong> program!</p>
        <p>To ensure we tailor our outreach efforts to your specific needs, please take a moment to fill out our client requirements form:</p>
        <p><a href="https://forms.gle/QzE1B9iDYJKVArnr6"><strong>Fill out the Client Requirements Form</strong></a></p>
        <p>Our dedicated outreach team is eager to connect with you to discuss your requirements and kick-off the program. We would like to schedule a brief kick-off meeting to understand your goals and set the stage for successful outreach.</p>
        <p>You can book a convenient slot for this meeting using our Google Calendar link:</p>
        <p><a href="https://calendar.app.google/45wvqajrQqNCpdPg6"><strong>Schedule Your Kick-off Meeting</strong></a></p>
        <p>If you have already booked a kick-off meeting slot, please disregard this section of the email.</p>
        <p>We're excited to help you achieve your outreach goals!</p>
        <p>Best regards,</p>
        <p>The Caprae Capital Team</p>
    '''
    send_email(subject, [recipient_email], html_body)