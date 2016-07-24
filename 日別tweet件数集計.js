db.getCollection('tweets').aggregate (
	{$project:{'jst_created_datetime':{$add:["$created_datetime", 9 * 60 * 60 * 1000]},
                   'retweet_count':'$retweet_count'}},
	{$group: 
		{ "_id"  : 
			{year: { $year: "$jst_created_datetime" }, 
			month: { $month: "$jst_created_datetime" }, 
			day: { $dayOfMonth: "$jst_created_datetime" } },
		"tweet_count" : { "$sum" : 1 }, 
		"retweet_count":{"$sum": "$retweet_count"} }
	}, 
	{$sort: {"_id":-1}}
)