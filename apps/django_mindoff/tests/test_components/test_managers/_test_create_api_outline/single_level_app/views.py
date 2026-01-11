from django_mindoff.components.api_kit import mo_api_kit
from django_mindoff.components.response_kit import mo_response_kit


def update_progress(name, weight=1):
    # dummy function for testing
    pass


class MindOffSampleAPI(mo_api_kit.MindoffAPIMixin):
    api_name = "Sample API Name"
    api_description = "Sample API Description"

    def run(self, request, *args, **kwargs):
        update_progress("1", weight=3)
        update_progress("2", weight=6)
        update_progress("3")
        return mo_response_kit.json_response(
            code="SUCCESS", category="success", data={}
        )
