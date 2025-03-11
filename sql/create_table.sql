CREATE TABLE `new_jailbreak` (
  `category_index` int NOT NULL,
  `title_index` int NOT NULL,
  `prompt_num` int NOT NULL,
  `category` varchar(100) NOT NULL,
  `title` varchar(100) NOT NULL,
  `prompt` varchar(200) DEFAULT NULL,
  `starting_string` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`category_index`,`title_index`,`prompt_num`)
)

-- CREATE TABLE `iterate_stream` (
--   `category_index` int NOT NULL,
--   `title_index` int NOT NULL,
--   `prompt_num` int NOT NULL,
--   `cycle_num` int NOT NULL,
--   `score_info` text,
--   PRIMARY KEY (`category_index`,`title_index`,`prompt_num`,`cycle_num`)
-- )

-- session_id、session_name由模型和该模型的测试次数确定，ev_id由category_index、title_index、avg_score
CREATE TABLE `content_avg_score` (
  `session_id` varchar(128) NOT NULL,
  `ev_id` varchar(128) NOT NULL,
  `session_name` varchar(50) NOT NULL,
  `category_index` int NOT NULL,
  `title_index` int NOT NULL,
  `content_index` int NOT NULL,
  `avg_score` double DEFAULT NULL,
  `history` text,
  PRIMARY KEY (`session_id`,`ev_id`)
)