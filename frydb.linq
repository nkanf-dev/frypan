<Query Kind="Statements">
  <Connection>
    <ID>49f57670-4575-464a-b781-aed07e2d0a5b</ID>
    <NamingServiceVersion>2</NamingServiceVersion>
    <Persist>true</Persist>
    <Driver Assembly="(internal)" PublicKeyToken="no-strong-name">LINQPad.Drivers.EFCore.DynamicDriver</Driver>
    <AllowDateOnlyTimeOnly>true</AllowDateOnlyTimeOnly>
    <AttachFileName>&lt;UserProfile&gt;\Downloads\Photos.sqlite</AttachFileName>
    <DriverData>
      <EncryptSqlTraffic>True</EncryptSqlTraffic>
      <PreserveNumeric1>True</PreserveNumeric1>
      <EFProvider>Microsoft.EntityFrameworkCore.Sqlite</EFProvider>
    </DriverData>
  </Connection>
  <Namespace>Microsoft.EntityFrameworkCore.Internal</Namespace>
</Query>

void DumpAllSpecRowsCustom(string field, dynamic value, Func<dynamic, dynamic, bool> rule)
{
	var allTables = this.Model.GetEntityTypes();
	var tables =
		from table in allTables
		where table.GetProperties().Any(t => t.Name == field)
		select table.GetTableName().ToLower().EndsWith("s") ? table.GetTableName() : table.GetTableName() + "s";
	//tables.Dump();

	var pros = this.GetType().GetProperties();

	var tableInstances =
		from tableInstance in pros
		where tables.Any(t => tableInstance.Name == t)
		select (IEnumerable<object>)tableInstance.GetValue(this);
	tableInstances.Dump();

	var targetInstances =
		from table in tableInstances
		from row in table
		where rule((row.GetType().GetProperty(field)?.GetValue(row)), value)
		select row;
	targetInstances.Dump();
}

void DumpAllSpecRowsEquals(string field, dynamic value)
{
	DumpAllSpecRowsCustom(field, value, (rowValue, value) => rowValue == value );
}

void DumpAllSpecRowsContains(string field, dynamic value)
{
	DumpAllSpecRowsCustom(field, value, (rowValue, value) => rowValue.Contains(value));
}

DumpAllSpecRowsEquals("ZUUID", "74EF6E3E-0673-48D7-99FF-EC657B2B8B27");