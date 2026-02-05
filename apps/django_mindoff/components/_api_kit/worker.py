import dramatiq
from django.test.client import RequestFactory
from .models import MOQueue
from .redis import update, get


@dramatiq.actor(acks_late=True, max_retries=0)
def execute_queue(queue_id):
    obj = MOQueue.objects.get(mo_queue_id=queue_id)

    if get(queue_id).get("cancelled"):
        update(queue_id, status="stop")
        obj.status = "stop"
        obj.save()
        return

    try:
        request = RequestFactory().post("/", data=obj.request)
        api = resolve(obj.api_url).func.view_class()

        response = api().run(request)

        update(queue_id, status="ok", progress=100)
        obj.status = "ok"
        obj.response = response
    except Exception as e:
        update(queue_id, status="fail", msg=str(e))
        obj.status = "fail"
        obj.error = {"error": str(e)}
    finally:
        obj.save()
