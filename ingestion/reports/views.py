from django.shortcuts import render, get_object_or_404
from .models import ReportCategory, Report

def report_list(request):
    categories = ReportCategory.objects.prefetch_related('reports').all()
    return render(request, 'reports/report_list.html', {'categories': categories})

def report_detail(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    # Logic to execute the report query and fetch data can be added here
    return render(request, 'reports/report_detail.html', {'report': report})
