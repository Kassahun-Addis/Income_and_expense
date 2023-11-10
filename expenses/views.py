from django.shortcuts import render, redirect
#from django.contrib.auth.decorators import login_required
from .models import Category, Expense
# # Create your views here.
from django.contrib import messages
# from django.contrib.auth.models import User
from django.core.paginator import Paginator
import json
from django.http import JsonResponse,HttpResponse
from userpreferences.models import UserPreference
import datetime
import csv
import xlwt

from django.template.loader import render_to_string
#from weasyprint import HTML
import tempfile
from django.db.models import Sum

from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

def search_expenses(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText')
        expenses = Expense.objects.filter(
            amount__istartswith=search_str, owner=request.user) | Expense.objects.filter(
            date__istartswith=search_str, owner=request.user) | Expense.objects.filter(
            description__icontains=search_str, owner=request.user) | Expense.objects.filter(
            category__icontains=search_str, owner=request.user)
        data = expenses.values()
        return JsonResponse(list(data), safe=False)


#@login_required(login_url='/authentication/login')
def index(request):
    categories = Category.objects.all()
    expenses = Expense.objects.filter(owner=request.user)
    paginator = Paginator(expenses, 5)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    currency = UserPreference.objects.get(user=request.user).currency
    context = {
        'expenses': expenses,
        'page_obj': page_obj,
        'currency': currency
    }
    return render(request, 'expenses/index.html', context)


# @login_required(login_url='/authentication/login')
def add_expense(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'values': request.POST
    }
    #return render(request, 'expenses/add_expense.html',context)
    if request.method == 'GET':
        return render(request, 'expenses/add_expense.html', context)

    if request.method == 'POST':
        amount = request.POST['amount']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/add_expense.html', context)
        description = request.POST['description']
        date = request.POST['expense_date']
        category = request.POST['category']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'expenses/add_expense.html', context)

        Expense.objects.create(owner=request.user, amount=amount, date=date,
                               category=category, description=description)
        messages.success(request, 'Expense saved successfully')

        return redirect('expenses')


# @login_required(login_url='/authentication/login')
def expense_edit(request, id):
    expense = Expense.objects.get(pk=id)
    categories = Category.objects.all()
    context = {
        'expense': expense,
        'values': expense,
        'categories': categories
    }
    if request.method == 'GET':
        #return render(request, 'expenses/edit-expense.html', context)
        return render(request, 'expenses/edit-expense.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']

        if not amount:
            messages.error(request, 'Amount is required')
            return render(request, 'expenses/edit-expense.html', context)
        description = request.POST['description']
        date = request.POST['expense_date']
        category = request.POST['category']

        if not description:
            messages.error(request, 'description is required')
            return render(request, 'expenses/edit-expense.html', context)

        expense.owner = request.user
        expense.amount = amount
        expense. date = date
        expense.category = category
        expense.description = description

        expense.save()
        messages.success(request, 'Expense updated  successfully')

        return redirect('expenses')


def delete_expense(request, id):
    expense = Expense.objects.get(pk=id)
    expense.delete()
    messages.success(request, 'Expense removed')
    return redirect('expenses')


def expense_category_summary(request):
    todays_date = datetime.date.today()
    six_months_ago = todays_date-datetime.timedelta(days=30*6)
    expenses = Expense.objects.filter(owner=request.user,
                                      date__gte=six_months_ago, date__lte=todays_date)
    finalrep = {}

    def get_category(expense):
        return expense.category
    category_list = list(set(map(get_category, expenses)))

    def get_expense_category_amount(category):
        amount = 0
        filtered_by_category = expenses.filter(category=category)

        for item in filtered_by_category:
            amount += item.amount
        return amount

    for x in expenses:
        for y in category_list:
            finalrep[y] = get_expense_category_amount(y)

    return JsonResponse({'expense_category_data': finalrep}, safe=False)


def stats_view(request):
    return render(request, 'expenses/stats.html')

def export_csv(request):
    try:
        response=HttpResponse(content_type='text/csv')
        response['Content-Disposition']='attachment; filename=Expenses'+\
            str(datetime.datetime.now())+'.csv'
            
        writer=csv.writer(response)
        writer.writerow(['Amount', 'Description', 'Category', 'Date'])
        
        expenses=Expense.objects.filter(owner=request.user)
        
        for expense in expenses:
            writer.writerow([expense.amount, expense.description,
                            expense.category,expense.date])
        return response
    except Exception as e:
        # Handle exceptions, log errors, etc.
        print(f"Error exporting CSV: {str(e)}")
        return HttpResponse("Error exporting CSV", status=500)
 
 
def export_excel(request):
    response=HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition']='attachment; filename=Expenses'+\
        str(datetime.datetime.now())+'.xls'
        
    wb=xlwt.Workbook(encoding='utf-8')
    ws=wb.add_sheet('Expenses')
    row_num=0
    font_style=xlwt.XFStyle()
    font_style.font_bold=True
    
    columns=['Amount', 'Description', 'Category', 'Date']
    
    for col_num in range(len(columns)):
        ws.write(row_num,col_num, columns[col_num],font_style)
    
    font_style=xlwt.XFStyle()
    
    rows=Expense.objects.filter(owner=request.user).values_list('amount', 'description', 'category', 'date')
    
    for row in rows:
        row_num  +=1   
        
        for col_num in range(len(row)):
            ws.write(row_num,col_num, str(row[col_num]),font_style)  
    wb.save(response)
               
    return response   





def export_pdf(request):
    # Create a response object with PDF content type
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; attachment; filename=Expenses' + \
        str(datetime.datetime.now()) + '.pdf'
    response['Content-Transfer-Encoding'] = 'binary'

    expenses = Expense.objects.filter(owner=request.user)

    # Calculate the total sum of expenses
    total_sum = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    # Render HTML template with data
    html_string = render_to_string('expenses/pdf-output.html', {'expenses': expenses, 'total': total_sum})

    # Create a BytesIO buffer to store the PDF content
    buffer = BytesIO()

    # Create a PDF document with a buffer
    pdf_document = SimpleDocTemplate(buffer, pagesize=letter)

    # Create a list to hold the data for the table
    table_data = [['No', 'Amount', 'Category', 'Description', 'Date']]

    # Add expense data to the table_data list
    for index, expense in enumerate(expenses, start=1):
        table_data.append([index, expense.amount, expense.category, expense.description, expense.date])

    # Add a row for the total
    table_data.append(['Total', total_sum])

    # Create a table style with specific column widths and row heights
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), '#377eb8'),  # Header background color
        ('TEXTCOLOR', (0, 0), (-1, 0), 'white'),     # Header text color
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),        # Center-align all cells
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Header font
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),      # Header padding
        ('BACKGROUND', (0, -1), (-1, -1), '#eeeeee'),  # Total row background color
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Total row font
    ])

    # Create the table and apply the style
    pdf_table = Table(table_data, repeatRows=1)
    pdf_table.setStyle(style)

    # Build the PDF document with the table
    pdf_document.build([pdf_table])

    # Rewind the buffer to the beginning
    buffer.seek(0)

    # Write the buffer content to the response
    response.write(buffer.read())

    return response

    
    
# All are passed!export-excel