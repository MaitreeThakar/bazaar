const payButton = document.getElementById('pay-button');
const couponInput = document.getElementById('coupon-code');
const statusMessage = document.getElementById('payment-status');

const csrfToken = document.querySelector(
    '[name=csrfmiddlewaretoken]'
).value;


// Send an authenticated POST request to a Django API endpoint.
async function postJSON(url, data) {
    const response = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(data)
    });

    const responseText = await response.text();

    let result;

    try {
        result = JSON.parse(responseText);
    } catch {
        console.error('Unexpected response from:', url);
        console.error('HTTP status:', response.status);
        console.error('Response body:', responseText);

        throw new Error(
            `Server returned a non-JSON response (HTTP ${response.status}). ` +
            'Check the browser console.'
        );
    }

    if (!response.ok) {
        throw new Error(
            result.error || result.detail || 'The request failed.'
        );
    }

    return result;
}

// Create the Razorpay order and open Checkout.
payButton.addEventListener('click', async function () {
    payButton.disabled = true;
    statusMessage.textContent = 'Preparing your checkout...';

    try {
        const couponCode = couponInput.value.trim();

        const checkoutData = await postJSON(
            '/api/checkout/',
            couponCode ? { coupon_code: couponCode } : {}
        );
        console.log('Django Order ID:', checkoutData.django_order_id);
        console.log('Razorpay Order ID:', checkoutData.razorpay_order_id);

        statusMessage.textContent =
            `Django Order ID: ${checkoutData.django_order_id} | ` +
            `Razorpay Order ID: ${checkoutData.razorpay_order_id}`;


        statusMessage.textContent =
            `Django checkout created. Razorpay Order ID: ` +
            `${checkoutData.razorpay_order_id}. Opening payment...`;
        const options = {
            key: checkoutData.razorpay_key_id,
            amount: checkoutData.amount,
            currency: checkoutData.currency,
            name: 'Bazaar',
            description: 'Bazaar Order',
            order_id: checkoutData.razorpay_order_id,

            handler: async function (response) {
                statusMessage.textContent =
                    'Payment received. Verifying payment...';

                try {
                    const result = await postJSON(
                        '/api/payment-success/',
                        response
                    );

                    statusMessage.textContent =
                        result.message +
                        ' Django Order ID: ' + result.order_id;

                } catch (error) {
                    statusMessage.textContent =
                        'Payment verification failed: ' + error.message +
                        '. Check your order status before retrying.';
                } finally {
                    payButton.disabled = false;
                }
            },

            modal: {
                ondismiss: function () {
                    statusMessage.textContent =
                        'Checkout closed. The order may still be pending.';
                    payButton.disabled = false;
                }
            }
        };

        const razorpay = new Razorpay(options);

        razorpay.on('payment.failed', function (response) {
            statusMessage.textContent =
                'Payment failed: ' +
                (response.error.description || 'Please try again.');

            payButton.disabled = false;
        });

        razorpay.open();

    } catch (error) {
        statusMessage.textContent = error.message;
        payButton.disabled = false;
    }
});