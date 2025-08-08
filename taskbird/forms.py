# taskbird/forms.py
from django import forms
from taskbird.models import Ticket, Category, Priority, Status, TicketAttachment
from accounts.models import User


# from customer side
class TicketForm(forms.ModelForm):
    attachments = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'class': 'block w-full text-sm text-gray-700 border border-gray-300 rounded-lg shadow-sm file:bg-blue-50 file:border-0 file:px-4 file:py-2 file:rounded-full file:text-blue-700 hover:file:bg-blue-100'
        }),
        required=False,
        help_text="Upload a relevant file (max 5MB, JPEG/PNG/PDF)."
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'placeholder': 'Enter ticket title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
                'rows': 5,
                'placeholder': 'Describe your issue'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default priority (e.g., Low or ID=1)
        try:
            self.fields['priority'].initial = Priority.objects.get(id=1)
        except Priority.DoesNotExist:
            pass
        # Make category optional
        self.fields['category'].required = False

    def clean_attachments(self):
        file = self.cleaned_data.get('attachments')
        if file:
            max_size = 5 * 1024 * 1024  # 5MB
            allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
            if file.size > max_size:
                raise forms.ValidationError(f"File {file.name} exceeds 5MB limit.")
            if file.content_type not in allowed_types:
                raise forms.ValidationError(f"File {file.name} is not a supported type (JPEG, PNG, PDF).")
        return file
    

# Ticket form from agent side
class TicketAgentForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = (
            'title',
            'description',
            'category',
            'priority',
            'status',
            'channel',
            # 'agent',
            'customer'
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'}),
            'priority': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'}),
            'status': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'}),
            'channel': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'}),
            # 'agent': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'}),
            'customer': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'}),
        }

    def __init__(self, *args, **kwargs):
        super(TicketAgentForm, self).__init__(*args, **kwargs)
        # Dynamically populate dropdowns from DB
        self.fields['category'].queryset = Category.objects.all()
        self.fields['priority'].queryset = Priority.objects.all().order_by('-level')  # Highest priority first
        self.fields['status'].queryset = Status.objects.all()
        self.fields['customer'].queryset = User.objects.filter(user_type=User.UserType.CUSTOMER)



# Ticket firlter form
class TicketFilterForm(forms.Form):
    customer = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type=User.UserType.CUSTOMER),
        required=False,
        label="customer",
        widget=forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'})
    )

    agent = forms.ModelChoiceField(
        queryset=User.objects.filter(user_type=User.UserType.AGENT),
        required=False,
        label="agent",
        widget=forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'})
    )

    priority = forms.ModelChoiceField(
        queryset=Priority.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'})
    )

    status = forms.ModelChoiceField(
        queryset=Status.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'})
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'})
    )

    channel = forms.ChoiceField(
        choices=[('', '---------')] + list(Ticket.CHANNEL_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded'})
    )

    from_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full p-2 border border-gray-300 rounded'
        })
    )

    to_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full p-2 border border-gray-300 rounded'
        })
    )