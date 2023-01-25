from django.template.defaulttags import register


@register.inclusion_tag("helpers/utilization_graph.html")
def progress_graph(utilization, warning_threshold=101, danger_threshold=101):
    return {
        "utilization": utilization,
        "warning_threshold": warning_threshold,
        "danger_threshold": danger_threshold,
    }


@register.inclusion_tag("software_manager/my_render_field.html")
def my_render_field(field, bulk_nullable=False, label=None, label_text=None):
    return {
        "field": field,
        "label": label or field.label,
        "bulk_nullable": bulk_nullable,
        "label_text": label_text or "Set Null",
    }


@register.filter
def get_current_version(device):
    return device.custom_field_data.get("sw_version", None)


@register.filter
def cut_job_id(job_id):
    try:
        if len(job_id) > 10:
            return f"{job_id[:4]}...{job_id[-4:]}"
    except Exception:
        pass
    return job_id
