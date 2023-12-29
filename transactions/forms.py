from django import forms
from django.contrib.auth.models import User
from .models import Transaction,TransferAccount
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'amount',
            'transaction_type'
        ]

    def __init__(self, *args, **kwargs):
        self.account = kwargs.pop('account') # account value ke pop kore anlam
        super().__init__(*args, **kwargs)
        self.fields['transaction_type'].disabled = True # ei field disable thakbe
        self.fields['transaction_type'].widget = forms.HiddenInput() # user er theke hide kora thakbe

    def save(self, commit=True):
        self.instance.account = self.account
        self.instance.balance_after_transaction = self.account.balance
        return super().save()


class DepositForm(TransactionForm):
    def clean_amount(self): # amount field ke filter korbo
        min_deposit_amount = 100
        amount = self.cleaned_data.get('amount') # user er fill up kora form theke amra amount field er value ke niye aslam, 50
        if amount < min_deposit_amount:
            raise forms.ValidationError(
                f'You need to deposit at least {min_deposit_amount} $'
            )

        return amount


class WithdrawForm(TransactionForm):

    def clean_amount(self):
        account = self.account
        min_withdraw_amount = 500
        max_withdraw_amount = 20000
        balance = account.balance # 1000
        amount = self.cleaned_data.get('amount')
        if amount < min_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at least {min_withdraw_amount} $'
            )

        if amount > max_withdraw_amount:
            raise forms.ValidationError(
                f'You can withdraw at most {max_withdraw_amount} $'
            )

        if amount > balance: # amount = 5000, tar balance ache 200
            raise forms.ValidationError(
                f'You have {balance} $ in your account. '
                'You can not withdraw more than your account balance'
            )

        return amount



class LoanRequestForm(TransactionForm):
    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        return amount
    




class MoneyTransferForm(forms.ModelForm):
    
    class Meta:
        model = TransferAccount
        fields = ['amount', 'transfer_acc_no']

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        # transfer_acc=self.cleaned_data.get('transfer_acc_no')
        # print(amount)
        return amount 

    def __init__(self, *args, **kwargs):
        account = kwargs.pop('account', None)
        super(MoneyTransferForm, self).__init__(*args, **kwargs)
        if account:
            self.fields['transfer_acc_no'].queryset = User.objects.exclude(account=account)    


class TransferForm(forms.Form):
    amount = forms.DecimalField(max_digits=12, decimal_places=2, label='Amount')
    receiver_account_number = forms.CharField(max_length=20, label='Receiver Account Number')

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError("Amount should be greater than zero.")
        return amount

    def clean_receiver_account_number(self):
        receiver_account_number = self.cleaned_data['receiver_account_number']
        return receiver_account_number