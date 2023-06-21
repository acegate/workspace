from django.shortcuts import render, get_list_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Agent, Dection, Report, Identify, Department, Employee
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.db.models import Count, Q
from django.core.paginator import Paginator
import os, json, psutil, random

@require_http_methods(['GET'])
def home(request):
    context = home_data('HOME')
    return render(request, 'main/home.html', context)

@require_http_methods(['POST'])
def get_updated_data(request):
    context = home_data('REALTIME')
    return JsonResponse(context)

def home_data(isFlag):
    report_list = Report.objects.filter(status=0).order_by('-report_no').select_related('dect_no', 'dect_no__emp_no', 'emp_no__depmt_no').values(
        'dect_no', 'create_at', 'dect_no__emp_no__emp_no', 'dect_no__emp_no__emp_name', 'dect_no__emp_no__depmt_no__depmt_name'
    )
    
    for report in report_list:
        employee = report['dect_no__emp_no__emp_no']
        identify = Identify.objects.filter(emp_no=employee).first()
        if identify:
            report['ip'] = identify.ip
            report['mac'] = identify.mac

    dection_list = Dection.objects.filter(status=0).order_by('-dect_no').select_related('emp_no', 'emp_no__depmt_no').values(
        'dect_no', 'create_at', 'emp_no__emp_no', 'emp_no__emp_name', 'emp_no__depmt_no__depmt_name'
    )
    
    for dection in dection_list:
        employee = dection['emp_no__emp_no']
        identify = Identify.objects.filter(emp_no=employee).first()
        if identify:
            dection['ip'] = identify.ip
            dection['mac'] = identify.mac


    dect_count = Dection.objects.all().filter(status=0).aggregate(count=Count('dect_no'))
    report_count = Report.objects.all().filter(status=0).aggregate(count=Count('report_no'))
    report_done_count = Dection.objects.all().filter(status=1).aggregate(count=Count('dect_no'))
    
    if isFlag == 'HOME':
        context = {
            'dection_list' : dection_list,
            'report_list' : report_list,
            'dect_count' : dect_count['count'],
            'report_count' : report_count['count'],
            'report_done_count' : report_done_count['count'],
        }
    else:
        context = {
            'dection_list' : list(dection_list),
            'report_list' : list(report_list),
            'dect_count' : dect_count['count'],
            'report_count' : report_count['count'],
            'report_done_count' : report_done_count['count'],
        }

    return context


@require_http_methods(['GET', 'POST'])
def agent(request):
    if request.method == 'GET':

        page = request.GET.get('page', '1')
        search_key = request.GET.get('search_key')
        if search_key == None:
            search_key = ''

        agent_list = (
            Agent.objects
            .filter(identifies__emp_no__emp_name__icontains=search_key)
            .order_by('-agent_no')
            .prefetch_related('identifies__emp_no__depmt_no')
            .values(
                'agent_no',
                'create_at',
                'status',
                'identifies__ip',
                'identifies__mac',
                'identifies__emp_no__emp_name',
                'identifies__emp_no__email',
                'identifies__emp_no__rank',
                'identifies__emp_no__depmt_no__depmt_name',
                'identifies__emp_no__depmt_no__location',
                'identifies__emp_no__depmt_no__landline',
                'identifies__emp_no__phone_no',
            )
        )


        paginator = Paginator(agent_list, 10)
        page_obj = paginator.get_page(page)

        context = {
            'agent_list' : page_obj,
        }

        return render(request, 'main/agent.html', context)
    else:
        pass


def get_cpu_usage():
    cpu_percent = psutil.cpu_percent(interval=1)
    return cpu_percent

def detail(request):
    page = request.GET.get('page', '1')
    search_key = request.GET.get('search_key')
    search_mode = request.GET.get('search_mode')

    if search_key == None:
        search_key = ''

    if search_mode == None:
        search_mode = '0'

    dection_list = mode(stauts=search_mode, search_key=search_key)

    paginator = Paginator(dection_list, 10)
    page_obj = paginator.get_page(page)

    context = {
        'dection_list' : page_obj,
    }

    return render(request, 'main/detail.html', context)

def mode(stauts, search_key):
    if stauts == '0':
        dection_list = Dection.objects.filter(dect_no__icontains=search_key).order_by('-dect_no').select_related('emp_no', 'emp_no__depmt_no').values(
            'dect_no', 'create_at', 'status', 'emp_no__emp_no', 'emp_no__emp_name', 'emp_no__depmt_no__depmt_name'
        )
    elif stauts == '1':
        dection_list = Dection.objects.filter(
            emp_no__emp_name__icontains=search_key
        ).order_by('-dect_no').select_related('emp_no', 'emp_no__depmt_no').values(
            'dect_no', 'create_at', 'status', 'emp_no__emp_no', 'emp_no__emp_name', 'emp_no__depmt_no__depmt_name'
        )
    elif stauts == '2':
        dection_list = Dection.objects.order_by('-dect_no').select_related('emp_no', 'emp_no__depmt_no').values(
            'dect_no', 'create_at', 'status', 'emp_no__emp_no', 'emp_no__emp_name', 'emp_no__depmt_no__depmt_name'
        )
        
    elif stauts == '3':
        dection_list = Dection.objects.filter(
            emp_no__depmt_no__depmt_name__icontains=search_key
        ).order_by('-dect_no').select_related('emp_no', 'emp_no__depmt_no').values(
            'dect_no', 'create_at', 'status', 'emp_no__emp_no', 'emp_no__emp_name', 'emp_no__depmt_no__depmt_name'
        )

    elif stauts == '4':
        if search_key == '미처리':
            search_key = 0
        elif search_key == '대기중':
            search_key = 1
        elif search_key == '처리완료':
            search_key = 2

        dection_list = Dection.objects.filter(
            status__icontains=search_key
        ).order_by('-dect_no').select_related('emp_no', 'emp_no__depmt_no').values(
            'dect_no', 'create_at', 'status', 'emp_no__emp_no', 'emp_no__emp_name', 'emp_no__depmt_no__depmt_name'
        )

    for dection in dection_list:
        employee = dection['emp_no__emp_no']
        identify = Identify.objects.filter(emp_no=employee).first()
        if identify:
            dection['ip'] = identify.ip
            dection['mac'] = identify.mac

    return dection_list

@require_http_methods(['GET', 'POST'])
def process(request, dect_no):
    if request.method == 'GET':
        dect_one = Dection.objects.select_related('emp_no', 'emp_no__depmt_no').values(
            'dect_no', 'create_at', 'cam_path', 'emp_no', 'status', 'screen_path', 'emp_no__emp_img_path', 'emp_no__emp_no', 'emp_no__emp_name', 'emp_no__rank', 
            'emp_no__depmt_no__depmt_name', 'emp_no__email', 'emp_no__phone_no', 'emp_no__depmt_no__location', 'emp_no__depmt_no__landline',
        ).get(dect_no=dect_no)
        identify = Identify.objects.get(emp_no=dect_one['emp_no'])

        report_list = Report.objects.filter(dect_no=dect_no).values(
            'report_no', 'create_at', 'content', 'status'
        )

        context = {
            'dect_one' : dect_one,
            'report_list' : report_list,
            'identify' : identify,
        }
        return render(request, 'main/process.html', context)
    else:
        data = json.loads(request.body)
        status = int(data['result'])
        
        dection = Dection.objects.filter(dect_no=dect_no).update(status=status)

        if status == 2:
            contents = []
            report = Report()
            report.dect_no = dect_no
            with open(settings.MEDIA_ROOT + '/context.txt', 'r', encoding='utf-8') as file:
                for line in file:
                    if line == '\n':
                        continue
                    contents.append(line)
            rnd_content = random.choice(contents)
            report.content = rnd_content
            report.save()

        return JsonResponse({'sucess' : 200})

def employee(request):
    return render(request, 'main/employee.html')

@require_http_methods(['POST', 'GET'])
def addEmp(request):
    if request.method == 'GET':
        dempt_list = Department.objects.all()
        context = {
            'dempt_list' : dempt_list,
        }
        return render(request, 'main/addEmp.html', context)
    else:
        error_message = "파일형식이 잘못되었습니다"
        context = {
            'message' : error_message,
        }
        STATUS = 400
        fs = FileSystemStorage()

        if 'file_csv' in request.FILES:
            csv_file = request.FILES['file_csv']
            allowed_extensions = ['csv', 'xlsx']
            file_extension = csv_file.name.split('.')[-1].lower()

            if file_extension not in allowed_extensions:
                return JsonResponse(context, status=STATUS)
    
            employee_csv_folder = 'employee_csv'
            employee_csv_path = os.path.join(employee_csv_folder, csv_file.name)
            csv_filename = fs.save(employee_csv_path, csv_file)
            return JsonResponse({'success': True})

        emp_img = request.FILES['empt_img']
        allowed_extensions = ['png', 'jpg', 'jpeg', 'bmp']
        file_extension = emp_img.name.split('.')[-1].lower()

        if file_extension not in allowed_extensions:
            return JsonResponse(context, status=STATUS)

        emp_name =request.POST.get('emp_name')
        rank = request.POST.get('rank')
        emp_no = request.POST.get('emp_no')
        MAC = request.POST.get('MAC')
        IP = request.POST.get('IP')
        phone_no = request.POST.get('phone_no')
        email = request.POST.get('email')
        depmt_no = request.POST.get('depmt_no')
        
        employee_folder = 'employee' 
        employee_path = employee_folder + '/' + f'{emp_no}_{emp_img.name}'
        filename = fs.save(employee_path, emp_img)

        employee = Employee()
        department = Department.objects.get(depmt_no=depmt_no)

        employee.emp_name = emp_name
        employee.emp_no = emp_no
        employee.depmt_no = department
        employee.rank = rank
        employee.phone_no = phone_no
        employee.email = email
        employee.emp_img_path = os.path.join(settings.MEDIA_URL, employee_path)
        employee.save()

        agent = Agent()
        agent.agent_no = emp_no
        agent.status = 0
        agent.save()

        identify = Identify()
        employee = Employee.objects.get(emp_no=emp_no)
        agent = Agent.objects.get(agent_no=emp_no)

        identify.emp_no = employee
        identify.agent_no = agent
        identify.ip = IP
        identify.mac = MAC
        identify.save()
        return JsonResponse({'success': True})

@require_http_methods(['POST', 'GET'])
def addDepart(request):
    if request.method == 'GET':
        return render(request, 'main/addDepart.html')
    else:
        reqData = json.loads(request.body)
        landline = reqData['landline']
        location = reqData['location']
        demp_name = reqData['demp_name']

        department = Department()
        department.landline = landline
        department.location = location
        department.depmt_name = demp_name
        department.save()

        # dempt_list = Department.objects.all()
        # depmt_name_list = serializers.serialize('json', department)
        return JsonResponse(reqData)


        




