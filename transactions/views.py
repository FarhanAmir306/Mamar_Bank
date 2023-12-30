from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts.models import UserBankAccount
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView,FormView
from transactions.constants import DEPOSIT, WITHDRAWAL, LOAN, LOAN_PAID,TRANSFER
from datetime import datetime
from django.db.models import Sum
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string
from accounts.forms import ChangePasswordForm  
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages

from transactions.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    # MoneyTransferForm,
    TransferForm,
)
from transactions.models import Transaction,TransferAccount


def send_transaction_mail(user,amount,subject,template):
        
        massage=render_to_string(template,{
            'user':user,
            'amount':amount
        })
        send_email=EmailMultiAlternatives(subject,'',to=[user.email])
        send_email.attach_alternative(massage,'text/html')
        send_email.send()


class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = "transactions/transaction_form.html"
    model = Transaction
    title = ""
    success_url = reverse_lazy("transaction_report")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if hasattr(self.request.user, 'account'):
            kwargs.update({"account": self.request.user.account})
        else:
            kwargs.update({"account": None})

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )  # template e context data pass kora
        context.update({"title": self.title})

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = "Deposit"

    def get_initial(self):
        initial = {"transaction_type": DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get("amount")
       
        account = self.request.user.account
        # if not account.initial_deposit_date:
        #     now = timezone.now()
        #     account.initial_deposit_date = now
        account.balance += (
            amount  # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
        )
        account.save(update_fields=["balance"])

        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully',
        )

        send_transaction_mail(self.request.user,amount,'Deposit Massage','transactions/deposit_mail.html')

        return super().form_valid(form)
    


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = "Withdraw Money"

    def get_initial(self):
        initial = {"transaction_type": WITHDRAWAL}
        return initial

    def form_valid(self, form):
        user_account = self.request.user.account
        is_bankrupt = user_account.bankrupt
        amount = form.cleaned_data.get("amount")  # Define amount here

        if not is_bankrupt:
            self.request.user.account.balance -= amount
            self.request.user.account.save(update_fields=["balance"])

            messages.success(
                self.request,
                f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account',
            )
        else:
            messages.error(
                self.request,
                f'Your Bank balance is Empty Because Bankrupt',
            )

        send_transaction_mail(
            self.request.user, amount, 'Withdraw Message', 'transactions/withdraw_mail.html'
        )

        return super().form_valid(form)




class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = "Request For Loan"

    def get_initial(self):
        initial = {"transaction_type": LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get("amount")
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account, transaction_type=3, loan_approve=True
        ).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully',
        )

        send_transaction_mail(self.request.user,amount,'Loan Request Massage','transactions/loan_request_mail.html')

        return super().form_valid(form)


class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = "transactions/transaction_report.html"
    model = Transaction
    balance = 0  # filter korar pore ba age amar total balance ke show korbe

    def get_queryset(self):
        queryset = super().get_queryset().filter(account=self.request.user.account)
        start_date_str = self.request.GET.get("start_date")
        end_date_str = self.request.GET.get("end_date")

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

            queryset = queryset.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            )
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum("amount"))["amount__sum"]
        else:
            self.balance = self.request.user.account.balance

        return queryset.distinct()  # unique queryset hote hobe

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"account": self.request.user.account})

        return context


class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
            # Reduce the loan amount from the user's balance
            # 5000, 500 + 5000 = 5500
            # balance = 3000, loan = 5000
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect("transactions:loan_list")
            else:
                messages.error(
                    self.request, f"Loan amount is greater than available balance"
                )

        return redirect("loan_list")


class LoanListView(LoginRequiredMixin, ListView):
    model = Transaction
    template_name = "transactions/loan_request.html"
    context_object_name = "loans"  # loan list ta ei loans context er moddhe thakbe

    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account, transaction_type=3)
        print(queryset)
        return queryset




from django.shortcuts import get_object_or_404
from django.views import View

class Money(View):

    def get(self, request, **kwargs):
        if "form" not in kwargs:
            kwargs["form"] = self.request
            kwargs["title"] = 'Transfer'
        return render(request, "transactions/transaction_form.html", context=kwargs)

    
    def post(self,request):
        print(request.POST['amount'])
        a = request.POST['amount']
        amount=int(a)
        sender_account = self.request.user.account
        receiver_account_number = request.POST['account']
        # print(amount,sender_account,receiver_account_number)
        receiver_account = get_object_or_404(UserBankAccount, account_no=receiver_account_number)
        print(receiver_account)
        print(type(sender_account.balance),type(int(amount)))

        if sender_account.balance >= amount:
            sender_account.balance -= amount
            sender_account.save(update_fields=['balance'])

            receiver_account.balance += amount
            receiver_account.save(update_fields=['balance'])

            # Create transaction records for sender and receiver
            Transaction.objects.create(
                account=sender_account,
                amount=-amount,  # Negative amount for sender (deduction)
                balance_after_transaction=sender_account.balance,
                transaction_type=TRANSFER,
                loan_approve=False,
            )

            Transaction.objects.create(
                account=receiver_account,
                amount=amount,  # Positive amount for receiver (addition)
                balance_after_transaction=receiver_account.balance,
                transaction_type=TRANSFER,
                loan_approve=False
            )

            messages.success(
                self.request,
                f'{"{:,.2f}".format(float(amount))}$ was transferred to {receiver_account_number}'
            )
            # sender
            send_transaction_mail(self.request.user,sender_account.balance,"Send Money",'transactions/sender_mail.html')
            send_transaction_mail(receiver_account.user,receiver_account.balance,"Recived Money",'transactions/recived_mail.html')
            return render(request,"transactions/transaction_form.html")
            
        return  redirect('transaction_report')
    

   






class TransferMoneyView(FormView):
    form_class = TransferForm 
    template_name="transactions/transaction_form.html"
    success_url=reverse_lazy('transaction_report')
  

    def get_context_data(self, **kwargs):
        if "form" not in kwargs:
            kwargs["form"] = self.get_form()
            kwargs["title"] = 'Transfer'
        return super().get_context_data(**kwargs)


    # def form_valid(self, form):
    #     print('hello')
    #     amount = form.cleaned_data.get('amount')
    #     sender_account = self.request.user.account
    #     receiver_account_number = form.cleaned_data.get('receiver_account_number')
    #     print(amount,sender_account,receiver_account_number)
    #     receiver_account = get_object_or_404(UserBankAccount, account_number=receiver_account_number)

    #     if sender_account.balance >= amount:
    #         sender_account.balance -= amount
    #         sender_account.save(update_fields=['balance'])

    #         receiver_account.balance += amount
    #         receiver_account.save(update_fields=['balance'])

    #         # Create transaction records for sender and receiver
    #         Transaction.objects.create(
    #             account=sender_account,
    #             amount=-amount,  # Negative amount for sender (deduction)
    #             balance_after_transaction=sender_account.balance,
    #             transaction_type=TRANSACTION_TYPE['TRANSFER'],
    #             loan_approve=False
    #         )

    #         Transaction.objects.create(
    #             account=receiver_account,
    #             amount=amount,  # Positive amount for receiver (addition)
    #             balance_after_transaction=receiver_account.balance,
    #             transaction_type=TRANSACTION_TYPE['TRANSFER'],
    #             loan_approve=False
    #         )

    #         messages.success(
    #             self.request,
    #             f'{"{:,.2f}".format(float(amount))}$ was transferred to {receiver_account_number}'
    #         )

    #         # Send notification emails or perform necessary actions

    # return super().form_valid(form)
        # else:
        #     messages.error(self.request, 'Insufficient balance for the transfer')
        #     return super().form_invalid(form)




from django.contrib.auth.decorators import login_required
@login_required(login_url='accounts/login/')
def pass_change(request):
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Password Updated Successfully')
            update_session_auth_hash(request, form.user)
            subject="Change Password"
            massage=render_to_string('transactions/change_pass_mail.html',{'user':request.user})
            send_email=EmailMultiAlternatives(subject,'',to=[request.user.email])
            send_email.attach_alternative(massage,'text/html')
            send_email.send()
            return redirect('profile')
    
    else:
        form = ChangePasswordForm(user=request.user)
    return render(request, 'accounts/pass_change.html', {'form' : form})