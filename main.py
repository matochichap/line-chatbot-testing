import os
import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent,
    TextMessage,
    TextSendMessage,
    FlexSendMessage,
    BubbleContainer,
    BoxComponent,
    TextComponent,
    SeparatorComponent,
    ButtonComponent,
    URIAction,
    CarouselContainer
)

app = Flask(__name__)

CHANNEL_SECRET = os.environ.get("channel_secret")
CHANNEL_ACCESS_TOKEN = os.environ.get("channel_access_token")
MENU = "Commands:\n" \
       "/echo <text> - returns user input\n" \
       "/1 - job listings(table)\n" \
       "/2 - job listings(carousel)"

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# testing
JOB_LISTINGS = json.load(open("job_listings.json"))


@app.route("/", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


def handle_message(event, line_bot_api):
    message_text = event.message.text
    if message_text.split(' ', 1)[0] == "/echo":
        reply_text = "You said: " + message_text.split(' ', 1)[1]
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        return
    if message_text == "/1":
        line_bot_api.reply_message(
            event.reply_token,
            create_job_listings_flex_message(JOB_LISTINGS)
        )
        return
    if message_text == "/2":
        line_bot_api.reply_message(
            event.reply_token,
            create_job_listings_carousel_message(JOB_LISTINGS)
        )
        return
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=MENU))


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
                    action=URIAction(uri=job["url"], label='Link')
                )
            ]
        )
        bubble_body.contents.append(job_box)

    bubble.body = bubble_body

    # Create the FlexMessage and return it
    return FlexSendMessage(alt_text="Job Listings", contents=bubble)


def create_job_listings_carousel_message(job_listings):
    bubbles = []

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
                TextComponent(text=job["description"], margin="sm", size="sm", wrap=True),
            ]
        )
        bubble_body.contents.append(job_description)

        job_website = BoxComponent(
            layout="horizontal",
            margin="md",
            contents=[
                TextComponent(text=job["url"], margin="sm", size="sm",
                              action=URIAction(uri=job["url"], label='Link'), color="#3b8132")
            ]
        )
        bubble_body.contents.append(job_website)

        bubble.body = bubble_body

        # Add the bubble to the list of bubbles
        bubbles.append(bubble)

    # Create a CarouselContainer for the FlexMessage
    carousel = CarouselContainer(contents=bubbles)

    # Create the FlexMessage and return it
    return FlexSendMessage(alt_text="Job Listings", contents=carousel)


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    handle_message(event, line_bot_api)


if __name__ == "__main__":
    app.run()
