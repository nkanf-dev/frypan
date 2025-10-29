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

QueryResult DumpAllSpecRowsCustom(string field, dynamic value, Func<string, string, bool> ruleField = null, Func<dynamic, dynamic, bool> ruleValue = null, bool dumpTablesFlag = true)
{
	// Default func for two rules.
	if (ruleField is null)
	{
		ruleField = (name, field) => name == field;
	}
	if (ruleValue is null)
	{
		ruleValue = (rowValue, value) => rowValue == value;
	}

	var allTables = this.Model.GetEntityTypes();
	var tables =
		from table in allTables
		where table.GetProperties().Any(t => ruleField(t.Name, field))
		select table.GetTableName().ToLower().EndsWith("s") ? table.GetTableName() : table.GetTableName() + "s";
	//tables.Dump();

	var fields =
		(from table in allTables
		from p in table.GetProperties()
		where ruleField(p.Name, field)
		select p.Name).Distinct().ToArray();
	//fields.Dump();

	var pros = this.GetType().GetProperties();

	var tableInstances =
		from pro in pros
		where tables.Any(t => pro.Name == t)
		select (IEnumerable<object>)pro.GetValue(this);
	if (dumpTablesFlag)
	{
		tableInstances.Dump($"Tables match field: {field}");
	}
	
	bool matchValues(object row, string[] fields, dynamic value, Func<dynamic, dynamic, bool> ruleValue) {
		foreach (var field in fields)
		{
			var a = (row.GetType().GetProperty(field)?.GetValue(row));
			if (ruleValue(a, value))
			{
				return true;
			}
		}
		return false;
	}
	
	var targetInstances =
		from table in tableInstances
		from row in table
		where matchValues(row, fields, value, ruleValue)
		select new {table, row};
	targetInstances.Dump($"Rows match value: {value}");
	return new QueryResult(tableInstances, targetInstances);
}

Func<string, string, bool> GetFieldRule(RuleType type, bool caseSensitive) {
	return (type, caseSensitive) switch {
		(RuleType.Equals, false) => (name, field) => name.ToLower() == field.ToLower(),
		(RuleType.Equals, true) => (name, field) => name == field,
		(RuleType.Contains, false) => (name, field) => name.ToLower().Contains(field.ToLower()),
		(RuleType.Contains, true) => (name, field) => name.Contains(field),
		_ => (name, field) => name == field,
	};
}

Func<dynamic, dynamic, bool> GetValueRule(RuleType type, bool caseSensitive)
{
	return (type, caseSensitive) switch
	{
		(RuleType.Equals, _) => (name, value) => (name is string ? name : (name is null ? "" : name.ToString())) == value,
		(RuleType.Contains, _) => (name, value) => (name is string ? name : (name is null ? "" : name.ToString())).Contains(value),
		_ => (name, value) => name == value,
	};
}

QueryResult DumpAllSpecRowsEqualsEquals(string field, dynamic value, bool dumpTablesFlag = true, bool caseSensitive = true)
{
	return DumpAllSpecRowsCustom(field, value, GetFieldRule(RuleType.Equals, caseSensitive), GetValueRule(RuleType.Equals, caseSensitive), dumpTablesFlag);
}

QueryResult DumpAllSpecRowsEqualsContains(string field, dynamic value, bool dumpTablesFlag = true, bool caseSensitive = true)
{
	return DumpAllSpecRowsCustom(field, value, GetFieldRule(RuleType.Equals, caseSensitive), GetValueRule(RuleType.Contains, caseSensitive), dumpTablesFlag);
}

QueryResult DumpAllSpecRowsContainsContains(string field, dynamic value, bool dumpTablesFlag = true, bool caseSensitive = true)
{
	return DumpAllSpecRowsCustom(field, value, GetFieldRule(RuleType.Contains, caseSensitive), GetValueRule(RuleType.Contains, caseSensitive), dumpTablesFlag);
}

QueryResult DumpAllSpecRowsContainsEquals(string field, dynamic value, bool dumpTablesFlag = true, bool caseSensitive = true)
{
	return DumpAllSpecRowsCustom(field, value, GetFieldRule(RuleType.Contains, caseSensitive), GetValueRule(RuleType.Equals, caseSensitive), dumpTablesFlag);
}

List<QueryResult> DumpAllSpecRowsFieldsEqualsEquals(string[] fields, dynamic value, bool caseSensitive = true)
{
	List<QueryResult> result = new();
	foreach (var field in fields)
	{
		result.Add(DumpAllSpecRowsEqualsEquals(field, value, default, caseSensitive));
	}
	return result;
}

List<QueryResult> DumpAllSpecRowsEqualsValuesEquals(string field, dynamic[] values, bool caseSensitive = true)
{
	List<QueryResult> result = new();
	bool firstFlag = true;
	foreach (var value in values)
	{
		result.Add(DumpAllSpecRowsEqualsEquals(field, value, firstFlag, caseSensitive));
		if (firstFlag)
		{
			firstFlag = false;
		}
	}
	return result;
}

List<QueryResult> DumpAllSpecRowsContainsValuesEquals(string field, dynamic[] values, bool caseSensitive = true)
{
	List<QueryResult> result = new();
	bool firstFlag = true;
	foreach (var value in values)
	{
		result.Add(DumpAllSpecRowsContainsEquals(field, value, firstFlag, caseSensitive));
		if (firstFlag)
		{
			firstFlag = false;
		}
	}
	return result;
}

List<QueryResult> DumpAllSpecRowsEqualsValuesContains(string field, dynamic[] values, bool caseSensitive = true)
{
	List<QueryResult> result = new();
	bool firstFlag = true;
	foreach (var value in values)
	{
		result.Add(DumpAllSpecRowsEqualsContains(field, value, firstFlag, caseSensitive));
		if (firstFlag)
		{
			firstFlag = false;
		}
	}
	return result;
}

List<QueryResult> DumpAllSpecRowsContainsValuesContains(string field, dynamic[] values, bool caseSensitive = true)
{
	List<QueryResult> result = new();
	bool firstFlag = true;
	foreach (var value in values)
	{
		result.Add(DumpAllSpecRowsContainsContains(field, value, firstFlag, caseSensitive));
		if (firstFlag)
		{
			firstFlag = false;
		}
	}
	return result;
}

//DumpAllSpecRowsEqualsEquals("ZASSET", "9");
//DumpAllSpecRowsEqualsContains("ZLENSMODEL", "back");
//DumpAllSpecRowsEqualsValuesEquals("ZASSET", ["2","5","4","6"]);
//DumpAllSpecRowsContainsEquals("ZKINDS", "2");
//DumpAllSpecRowsEqualsValuesEquals("ZUUID", ["74EF6E3E-0673-48D7-99FF-EC657B2B8B27", "D1F333D7-718B-42DA-9B28-D936EDAFC58F"]);
//var allUUIDs = 
//	from row in ZASSETs
//	select row.ZUUID;
//DumpAllSpecRowsContainsValuesEquals("UUID", allUUIDs.ToArray(), false);




record QueryResult(IEnumerable<object> Tables, IEnumerable<object> Rows);
enum RuleType {
	Equals,
	Contains
}