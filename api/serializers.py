from rest_framework import serializers
from bazaar.models import Product,CartItem,Cart,OrderItem,Order,Account
from django.contrib.auth.models import User

# Serializer used for validating and creating a new user and account.
class SignUpSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField()
    role = serializers.ChoiceField(choices=["customer","supplier"])

    # Passwords are accepted as input but are not included in the response.
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    # Check whether the username is already taken.
    def validate_username(self,value): # for each field validation we have a method validate_<fieldname>
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    # Check whether the email is already registered.
    def validate_email(self,value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

    # Check that both passwords are the same.
    def validate(self, attrs): #here more than one field is in validation so we use validate method with attr
        if attrs["password"]!=attrs["confirm_password"]:
            raise serializers.ValidationError({ "confirm_password": "Passwords do not match." })
        return attrs

    # Create the User and its related Account after validation.
    def create(self, validated_data):
        # confirm_password is only used for validation, so remove it.
        validated_data.pop("confirm_password")

        # Create the Django User and securely hash the password.
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )

        # Create the Account linked to the new user.
        Account.objects.create(
            user=user,
            role=validated_data['role'],
            phone =validated_data['phone']
            
        )
        return user

# Serializer for displaying and creating products.
class ProductSerializer(serializers.HyperlinkedModelSerializer):
    # Show the supplier's username instead of the User object.
    supplier = serializers.ReadOnlyField(source= 'supplier.username')

    class Meta:
        model = Product
        fields = ['url','name','price','description','supplier']

# Serializer for displaying cart items.
class CartItemSerializer(serializers.HyperlinkedModelSerializer):
    # Show the username of the customer who owns the cart.
    customer = serializers.ReadOnlyField(source= 'cart.customer.username')
    class Meta:
        model = CartItem
        fields = ['url','customer','product','quantity']

# Serializer for displaying a customer's cart.
class CartSerializer(serializers.HyperlinkedModelSerializer):
    customer = serializers.ReadOnlyField(source= 'customer.username')

    # Include all items belonging to this cart.
    items = CartItemSerializer(many=True,read_only=True)

    # Extra calculated fields for the cart.
    total_items = serializers.SerializerMethodField()
    total_quantity= serializers.SerializerMethodField()
    cart_total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['url','customer','items','total_items','total_quantity','cart_total']

    #count number of different items in the cart
    def get_total_items(self,obj):
        return obj.items.count()

    #sum of all items
    def get_total_quantity(self,obj):
        return sum(item.quantity for item in obj.items.all())

    #cart total
    def get_cart_total(self,obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())

# Serializer for displaying individual order items.
class OrderItemSerializer(serializers.HyperlinkedModelSerializer):
    # Calculate the total price for this order item.
    item_total = serializers.SerializerMethodField()
    class Meta:
        model = OrderItem
        fields = [ 'product','quantity','price','item_total']

    def get_item_total(self,obj):
        return obj.quantity * obj.price  

# Serializer for displaying orders.
class OrderSerializer(serializers.ModelSerializer):
    # Show usernames and coupon codes instead of related objects.
    customer = serializers.ReadOnlyField(source= 'customer.username')
    coupon = serializers.ReadOnlyField(source= 'coupon.code')

    # Items are customized based on the logged-in user's role.
    items = serializers.SerializerMethodField()


    class Meta:
        model = Order
        fields = [
                  'url','items',
                  'customer', 'coupon', 
                  'total', 'discount', 
                  'final_total', 
                  'payment_status']

    # Return the order items that the current user is allowed to see.
    def get_items(self,obj):
        request = self.context['request']
        user = request.user

        # Get all items belonging to this order.
        items = obj.items.all()

        # Suppliers should only see their own products in the order.
        if user.account.role == 'supplier':
            items=[
                item for item in items
                if item.product.supplier == user
            ]
        # Use OrderItemSerializer to convert the items into response data.
        return OrderItemSerializer(
            items,many=True, context = self.context
        ).data

