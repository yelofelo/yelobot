async def save_roles(member, mongo_db):
    collection = mongo_db['LeaverRoles']

    roles = [role.id for role in member.roles if role.name != '@everyone']

    collection.delete_many({'user_id': member.id, 'server_id': member.guild.id})
    collection.insert_one({'user_id': member.id, 'server_id': member.guild.id, 'roles': roles})

async def assign_roles(member, mongo_db):
    collection = mongo_db['LeaverRoles']

    doc = collection.find_one({'user_id': member.id, 'server_id': member.guild.id})
    if doc:
        await add_roles(member, doc['roles'])
        collection.delete_one(doc)

    return doc is not None

async def add_roles(member, role_ids):
    roles_to_add = []

    for role_id in role_ids:
        role = member.guild.get_role(int(role_id))
        if role and role.is_assignable():
            roles_to_add.append(role)
    
    await member.add_roles(*roles_to_add, reason='Member rejoined the server.')

async def assign_roles_on_startup_impl(bot, mongo_db):
    collection = mongo_db['LeaverRoles']
    servers_to_delete = set()

    for doc in collection.find():
        server = bot.get_guild(int(doc['server_id']))
        if server:
            member = server.get_member(int(doc['user_id']))
            if member:
                await add_roles(member, doc['roles'])
                collection.delete_one(doc)
        else:
            servers_to_delete.add(int(doc['server_id']))
    
    for server_id in servers_to_delete:
        collection.delete_many({'server_id': server_id})
