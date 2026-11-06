# Managing Data Sets

A [data set](/docs/concepts#data-set) is a workspace that holds the agents, integrations and content of one company, brand or department. Data sets are separate from each other: an agent only uses the content of its own data set, and access is granted per data set.

A single data set is enough to get started. Further data sets are useful for:

- **Multiple brands or departments**, managed within one Suvereo instance.
- **Experimentation**, for trying out different models and configurations.
- **Content language separation**, with one data set per language.

Data sets are managed under **Manage** → **Data Sets** in the left sidebar. The page lists the data sets, with **Manage Access**, **Integrations** and **Edit** next to each.

## Creating a Data Set

1. Go to **Manage** → **Data Sets** and click **New Data Set**.
2. Fill in the form:
   - **Name:** the name shown to users.
   - **Language Model:** the provider and the model that agents in this data set use. The lists contain the providers installed on the instance, see [model providers](/plugins/openai).
   - **Advanced settings:**
     - **Embedding Provider** and **Embedding Model:** the plugin and the model that turn content into embeddings for search.
     - **Vector Size:** the size of the embedding vector, 512 by default. Some models support only fixed sizes, in which case the field offers them as a list.
3. Click **Create**. You are taken to the integrations of the new data set, where you can connect the external systems it is fed from.

The embedding settings are fixed when the data set is created, because they determine how its content is stored. The name and the language model can be changed later.

## Editing and Deleting a Data Set

Click **Edit** next to the data set.

At the bottom of the edit page, **Delete Data Set** removes the data set together with its entities, agents, conversations and integrations. This cannot be undone.

## Controlling Access

A data set is visible to the users, service accounts and groups that hold a role on it, and to everyone who holds a global role granting access to all data sets. To grant access:

1. Go to **Manage** → **Data Sets** and click **Manage Access** next to the data set.
2. Select a user, service account or group, select a data set role, and click **Add**.

The list below shows who holds which role on the data set. **Remove** takes a role away. For a group, the member count links to the list of its members, since a role granted to a group reaches all of them.

Roles and groups are described in [Roles and Groups](/docs/management/roles-and-groups).
