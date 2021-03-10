from django.template.defaulttags import register


@register.inclusion_tag('software_manager/my_render_field.html')
def my_render_field(field, start_now=False):
    return {
        'field': field,
        'start_now': start_now,
    }


@register.inclusion_tag('utilities/templatetags/utilization_graph.html')
def progress_graph(utilization, warning_threshold=101, danger_threshold=101):
    return {
        'utilization': utilization,
        'warning_threshold': warning_threshold,
        'danger_threshold': danger_threshold,
    }


@register.filter
def get_current_version(device):
    return device.custom_field_data.get('sw_version', None)


@register.filter
def cut_job_id(job_id):
    try:
        if len(job_id) > 10:
            return f'{job_id[:4]}...{job_id[-4:]}'
    except Exception:
        pass
    return job_id
