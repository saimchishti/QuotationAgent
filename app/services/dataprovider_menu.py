# RESTAURANT-AGENT-MAIN/app/services/dataprovider_menu.py

from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict

from app.db.models import (
    Menu,
    MenuIngredient,
    InventoryCase1,
    UnitCase1Type,
    MenuCategory,
    BusinessOwnerInventory,
    MenuPriceHistory
)

# --- 1. Menu Item Manager ---
async def get_menu_items_with_ingredients(db: AsyncSession, business_owner_id: int):
    """
    Fetches all menu items for a business owner, including their ingredients.
    """
    query = (
        select(Menu)
        .options(
            joinedload(Menu.menu_ingredients).joinedload(MenuIngredient.ingredient).joinedload(InventoryCase1.unit_type)
        )
        .where(Menu.business_owner_id == business_owner_id)
    )
    result = await db.execute(query)
    return result.unique().scalars().all()

# --- 2. Menu Category Overview ---
async def get_menu_by_category(db: AsyncSession, business_owner_id: int):
    """
    Fetches all menu items grouped by their category for a business owner.
    """
    query = (
        select(Menu)
        .join(Menu.menu_category)
        .options(joinedload(Menu.menu_category))
        .where(Menu.business_owner_id == business_owner_id)
        .order_by(MenuCategory.value)
    )
    result = await db.execute(query)
    return result.scalars().all()

# --- 3. Item Availability Tracker ---
async def get_menu_item_availability(db: AsyncSession, business_owner_id: int):
    """
    Checks the availability of each menu item based on ingredient stock levels.
    """
    # Get all ingredients required for all menu items for this owner
    menu_ingredients_query = (     
        select(
            Menu.id.label("menu_id"),
            Menu.name.label("menu_name"),
            MenuIngredient.ingredient_id,
            InventoryCase1.name.label("ingredient_name"), # <-- Fetch the name
            MenuIngredient.quantity
        )
        .join(MenuIngredient, Menu.id == MenuIngredient.menu_id)
        .join(InventoryCase1, MenuIngredient.ingredient_id == InventoryCase1.id) # <-- Add the join
        .where(Menu.business_owner_id == business_owner_id)
    )
    menu_ingredients_result = await db.execute(menu_ingredients_query)
    
    # Structure required ingredients by menu item
    required_ingredients = defaultdict(list)
    for row in menu_ingredients_result.fetchall():
        required_ingredients[row.menu_id].append({
            "menu_name": row.menu_name,
            "ingredient_id": row.ingredient_id,
            "ingredient_name": row.ingredient_name, # <-- Store the name
            "quantity_needed": float(row.quantity or 0)
        })

    # Get current stock for all ingredients for this owner
    inventory_stock_query = (
        select(BusinessOwnerInventory.inventory_id, BusinessOwnerInventory.stock_quantity)
        .where(BusinessOwnerInventory.business_owner_id == business_owner_id)
    )
    inventory_stock_result = await db.execute(inventory_stock_query)
    current_stock = {row.inventory_id: row.stock_quantity for row in inventory_stock_result.fetchall()}

    # Determine availability
    availability_status = []
    for menu_id, ingredients in required_ingredients.items():
        is_available = True
        missing_ingredients = []
        menu_name = ingredients[0]['menu_name']

        for ingredient in ingredients:
            stock_on_hand = current_stock.get(ingredient['ingredient_id'], 0)
            if stock_on_hand < ingredient['quantity_needed']:
                is_available = False
                missing_ingredients.append({
                    "id":ingredient['ingredient_id'],
                    "name": ingredient['ingredient_name']
                    })
        
        availability_status.append({
            "menu_id": menu_id,
            "menu_name": menu_name,
            "status": "Available" if is_available else "Unavailable",
            "missing_ingredients": missing_ingredients
        })
        
    return availability_status

# --- 4. Menu Change Log Viewer ---
async def get_menu_price_history(db: AsyncSession, business_owner_id: int):
    """
    Fetches the price change history for all menu items for a business owner.
    """
    query = (
        select(MenuPriceHistory)
        .join(Menu, MenuPriceHistory.menu_id == Menu.id)
        .where(Menu.business_owner_id == business_owner_id)
        .options(joinedload(MenuPriceHistory.menu))
        .order_by(MenuPriceHistory.effective_date.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()

