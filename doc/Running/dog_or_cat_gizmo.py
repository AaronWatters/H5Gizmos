
from H5Gizmos import Html, serve, schedule_task, get, do, Button

async def task():
    image = Html('<img src="local_files/dog.png" width="200" height="200"/>')
    image.serve_folder("local_files", "./example_folder")
    await image.show()
    info = image.add("Put image info here.")

    async def show_image_info_task():
        element = image.element
        src = await get(element.attr("src"))
        info.text("src =" + repr(src))

    def show_cat(*args):
        do(image.element.attr("src", "local_files/cat.jpg"))
        schedule_task(show_image_info_task())

    image.add(Button("Show cat", on_click=show_cat))

    def show_dog(*args):
        do(image.element.attr("src", "local_files/dog.png"))
        schedule_task(show_image_info_task())

    image.add(Button("Show dog", on_click=show_dog))

    schedule_task(show_image_info_task())

serve(task())
