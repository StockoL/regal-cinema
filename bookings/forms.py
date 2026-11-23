from django import forms


class CancellationRequestForm(forms.Form):
    """A customer's request to cancel. The reason is optional: staff
    decide either way (4.22)."""

    reason = forms.CharField(
        label='Reason (optional)', required=False, max_length=1000,
        widget=forms.Textarea(attrs={'rows': 4}),
    )
