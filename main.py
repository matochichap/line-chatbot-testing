import os
import json
import random
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, abort, render_template
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    PostbackEvent,
    TextMessage,
    TextSendMessage,
    FlexSendMessage,
    TemplateSendMessage,
    BubbleContainer,
    CarouselContainer,
    BoxComponent,
    TextComponent,
    SeparatorComponent,
    ButtonComponent,
    URIAction,
    MessageAction,
    PostbackAction,
    QuickReplyButton,
    QuickReply,
    ButtonsTemplate
)

# States
ASK_NAME = 0
ASK_JOB = 1
PROCESS_NAME = 2
PROCESS_JOB = 3
DISPLAY_MENU = 4
ASK_QUESTION = 5
PROCESS_QUESTION = 6
EDIT_DETAILS = 7

app = Flask(__name__)
Bootstrap(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # in instance directory
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

CHANNEL_SECRET = os.environ.get("channel_secret")
CHANNEL_ACCESS_TOKEN = os.environ.get("channel_access_token")
STATE = ASK_NAME
NGROK_ENDPOINT = "https://712f-61-91-218-50.ngrok-free.app"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
job_listings = json.load(open("job_listings.json"))


# https://flask-sqlalchemy.palletsprojects.com/en/2.x/queries/
class Users(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(200), unique=True)
    name = db.Column(db.String(200), nullable=False)
    job = db.Column(db.String(200), nullable=False)
    state = db.Column(db.Integer, nullable=False)


with app.app_context():
    db.create_all()


@app.route("/", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@app.route('/job-details/<int:index>')
def job_details(index):
    try:
        index = int(index)
        if 0 <= index <= len(job_listings) - 1:
            score = random.randint(50, 100)
            feedback = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut " \
                       "labore et dolore magna aliqua. Integer enim neque volutpat ac tincidunt vitae semper quis lectus. " \
                       "Massa eget egestas purus viverra accumsan in nisl. Ut placerat orci nulla pellentesque dignissim. " \
                       "Nulla aliquet enim tortor at auctor urna nunc id cursus. Ut morbi tincidunt augue interdum velit " \
                       "euismod in. Amet venenatis urna cursus eget nunc. Mauris nunc congue nisi vitae suscipit. Sed " \
                       "enim ut sem viverra aliquet eget sit amet tellus. Facilisis gravida neque convallis a cras semper " \
                       "auctor neque vitae. Dictum non consectetur a erat nam at lectus. Orci eu lobortis elementum nibh " \
                       "tellus molestie nunc non blandit. Lectus quam id leo in vitae turpis massa sed elementum. At " \
                       "lectus urna duis convallis convallis tellus id interdum. "
            return render_template("job-details.html", job=job_listings[index], score=score, feedback=feedback)
        return "Nothing to see here"
    except ValueError:
        return "Nothing to see here"


def change_user_state(s, user):
    user.state = s
    db.session.commit()


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    current_user = Users.query.filter_by(user_id=user_id).first()
    # add user if not in db
    if not current_user:
        current_user = Users(
            user_id=user_id,
            name="",
            job="",
            state=ASK_NAME
        )
        db.session.add(current_user)
        db.session.commit()
    # ask user for name
    if current_user.state == ASK_NAME:
        ask_for_name(event)
        change_user_state(PROCESS_NAME, current_user)
        return
    # edit current user name
    if current_user.state == PROCESS_NAME:
        current_user.name = event.message.text
        db.session.commit()
        change_user_state(ASK_JOB, current_user)
    # ask user for job
    if current_user.state == ASK_JOB:
        ask_for_job(event)
        change_user_state(PROCESS_JOB, current_user)
        return
    # edit current user job
    if current_user.state == PROCESS_JOB:
        current_user.job = event.message.text
        db.session.commit()
        change_user_state(DISPLAY_MENU, current_user)
    # display menu
    if current_user.state == DISPLAY_MENU:
        line_bot_api.reply_message(event.reply_token, create_menu(current_user))
        return
    # echo user question
    if current_user.state == PROCESS_QUESTION:
        question = event.message.text
        process_question(event, question)
        change_user_state(DISPLAY_MENU, current_user)
        return
    # edit user details
    if current_user.state == EDIT_DETAILS:
        change_user_state(ASK_NAME, current_user)
        return


@handler.add(PostbackEvent)
def handle_postback(event):
    user_id = event.source.user_id
    current_user = Users.query.filter_by(user_id=user_id).first()
    postback_data = event.postback.data
    # Process the postback data and perform the corresponding action
    if postback_data == "option1":
        create_job_listings_carousel_message(event, job_listings)
    if postback_data == "option2":
        ask_for_question(event)
        change_user_state(PROCESS_QUESTION, current_user)
    if postback_data == "option3":
        change_user_state(ASK_NAME, current_user)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="Type something to continue:"))
    if postback_data == "option4":
        db.session.delete(current_user)
        db.session.commit()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="User profile deleted"))


def ask_for_name(event):
    reply = "What is your name?"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def ask_for_job(event):
    reply = "What job are you looking for?"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def ask_for_question(event):
    reply = "What is your question?"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def process_question(event, question):
    reply = f"You asked: {question}"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


def create_job_listings_flex_message(job_listings):
    # Create a BubbleContainer for the FlexMessage
    bubble = BubbleContainer(size="giga")

    # Add a title to the BubbleContainer
    bubble_header = BoxComponent(
        layout="horizontal",
        contents=[
            TextComponent(text="Job Listings", weight="bold", size="lg")
        ]
    )
    bubble.header = bubble_header

    # Add a separator between the header and the job listings
    bubble_body = BoxComponent(layout="vertical", contents=[SeparatorComponent()])

    job_header = BoxComponent(
        layout="horizontal",
        margin="lg",
        contents=[
            TextComponent(text="Title", weight="bold", size="sm"),
            TextComponent(text="Location", weight="bold", size="sm"),
            TextComponent(text="Website", weight="bold", size="sm")
        ]
    )
    bubble_body.contents.append(job_header)

    # Add each job listing as a separate box component in the BubbleContainer
    for job in job_listings:
        job_box = BoxComponent(
            layout="horizontal",
            margin="lg",
            contents=[
                TextComponent(text=job["title"], margin="sm", size="sm", wrap=True),
                TextComponent(text=job["location"], margin="sm", size="sm", wrap=True),
                ButtonComponent(
                    style='primary',
                    height='sm',
                    margin='25px',
                    action=URIAction(uri="http://127.0.0.1:5000/job-details", label='More details')
                )
            ]
        )
        bubble_body.contents.append(job_box)

    bubble.body = bubble_body

    # Create the FlexMessage and return it
    return FlexSendMessage(alt_text="Job Listings", contents=bubble)


def create_job_listings_carousel_message(event, job_listings):
    bubbles = []
    index = 0
    for job in job_listings:
        # create a job bubble
        bubble = BubbleContainer(size="giga")

        # Add a title to the BubbleContainer
        bubble_header = BoxComponent(
            layout="horizontal",
            contents=[
                TextComponent(text=job["title"], weight="bold", size="lg", wrap=True)
            ]
        )
        bubble.header = bubble_header

        # Add a separator between the header and the job details
        bubble_body = BoxComponent(layout="vertical", contents=[SeparatorComponent()])

        # Add the job details to the BubbleContainer
        job_location = BoxComponent(
            layout="horizontal",
            margin="md",
            contents=[
                TextComponent(text=job["location"], margin="sm", size="sm", wrap=True),
            ]
        )
        bubble_body.contents.append(job_location)

        job_description = BoxComponent(
            layout="horizontal",
            margin="md",
            contents=[
                TextComponent(text=job["shortDescription"], margin="sm", size="sm", wrap=True),
            ]
        )
        bubble_body.contents.append(job_description)

        job_website = BoxComponent(
            layout="horizontal",
            margin="md",
            contents=[
                TextComponent(text="More details here", margin="sm", size="sm",
                              action=URIAction(uri=f"http://127.0.0.1:5000/job-details/{index}", label='Link'),
                              color="#3b8132")
            ]
        )
        index += 1
        bubble_body.contents.append(job_website)

        bubble.body = bubble_body

        # Add the bubble to the list of bubbles
        bubbles.append(bubble)

    # Create a CarouselContainer for the FlexMessage
    carousel = CarouselContainer(contents=bubbles)

    # Create the FlexMessage and return it
    line_bot_api.reply_message(
        event.reply_token,
        FlexSendMessage(alt_text="Job Listings", contents=carousel)
    )


# problem: quick reply not compatible with laptop, only mobile
def create_quick_reply_buttons():
    # Create Quick Reply buttons
    quick_reply_buttons = [
        QuickReplyButton(action=MessageAction(label='Option 1', text='Selected Option 1')),
        QuickReplyButton(action=MessageAction(label='Option 2', text='Selected Option 2')),
        QuickReplyButton(action=MessageAction(label='Option 3', text='Selected Option 3'))
    ]

    # Create Quick Reply instance with the buttons
    quick_reply = QuickReply(items=quick_reply_buttons)

    # Create TextSendMessage with the Quick Reply
    reply_message = TextSendMessage(text='Please select an option:', quick_reply=quick_reply)
    return reply_message


# TODO: yes/no buttons
# TODO: drop down option menu(similar to yes/no)
def create_menu(current_user):
    buttons_template = ButtonsTemplate(
        title=f"Hi, {current_user.name}",
        text=f"Looking for: {current_user.job} jobs",
        actions=[
            PostbackAction(label="Job listings", data="option1"),
            PostbackAction(label="Ask me anything", data="option2"),
            PostbackAction(label="Edit details", data="option3"),
            PostbackAction(label="Delete profile", data="option4")
        ],
    )
    template_message = TemplateSendMessage(
        alt_text="Menu", template=buttons_template
    )
    return template_message

# TODO: reply to user message(may be the sender method in linebot.models.send_messages module)


if __name__ == "__main__":
    app.run(debug=True)

